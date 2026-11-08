// Local Linux-only Viewpoint adapter. No game or mod code is executed by loading this library.
#include <vulkan/vulkan.h>
#include "nvsdk_ngx.h"
#include "nvsdk_ngx_vk.h"
#include "nvsdk_ngx_helpers.h"
#include "nvsdk_ngx_helpers_vk.h"
#include <pthread.h>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <stdexcept>
#include <string>
#include <filesystem>
#include <sstream>
#include <cstdio>

namespace {
// NGX initialization can exceed a JVM render thread's stack. Run every SDK call
// on one persistent large-stack worker; the caller waits before touching Vulkan again.
class Worker {
    std::mutex serial, mutex;
    std::condition_variable cv;
    std::function<void()> task;
    bool ready=false, done=false, stop=false;
    pthread_t thread{};
    static void* entry(void* p) { static_cast<Worker*>(p)->loop(); return nullptr; }
    void loop() {
        std::unique_lock<std::mutex> lock(mutex);
        while (true) {
            cv.wait(lock,[&]{return ready||stop;});
            if(stop) return;
            auto fn=std::move(task); ready=false;
            lock.unlock(); fn(); lock.lock(); done=true; cv.notify_all();
        }
    }
public:
    Worker() {
        pthread_attr_t a; pthread_attr_init(&a);
        pthread_attr_setstacksize(&a,64u<<20);
        int r=pthread_create(&thread,&a,entry,this); pthread_attr_destroy(&a);
        if(r) throw std::runtime_error("cannot start NGX worker");
    }
    ~Worker() { {std::lock_guard<std::mutex> lock(mutex);stop=true;cv.notify_all();} pthread_join(thread,nullptr); }
    void run(std::function<void()> fn) {
        std::lock_guard<std::mutex> single(serial);
        std::unique_lock<std::mutex> lock(mutex);
        std::exception_ptr error;
        task=[&]{try {fn();}catch(...){error=std::current_exception();}};
        ready=true;done=false;cv.notify_all();cv.wait(lock,[&]{return done;});
        if(error) std::rethrow_exception(error);
    }
};
Worker& worker(){static Worker w;return w;}
std::string error, extensions;
std::wstring libraryPath, cachePath;
const wchar_t* searchPath=nullptr;
NVSDK_NGX_FeatureCommonInfo common{};
constexpr const char* PROJECT="3c3a1ca4-cbca-4eda-9170-e1b3bb2e61a1";
VkDevice device=VK_NULL_HANDLE;
NVSDK_NGX_Parameter* params=nullptr;
NVSDK_NGX_Handle* feature=nullptr;
bool initialized=false;
bool firstFrame=true;
unsigned inWidth=0,inHeight=0;
void ngx(NVSDK_NGX_Result r,const char* operation){
    if(NVSDK_NGX_FAILED(r)){char b[160];snprintf(b,sizeof b,"%s failed: NGX 0x%08x",operation,unsigned(r));throw std::runtime_error(b);}
}
void vk(VkResult r,const char* operation){if(r!=VK_SUCCESS)throw std::runtime_error(std::string(operation)+": "+std::to_string(r));}
template<class F> int guarded(F fn){try{worker().run(fn);error.clear();return 0;}catch(const std::exception& e){error=e.what();return -1;}}
NVSDK_NGX_FeatureDiscoveryInfo discovery(){
    NVSDK_NGX_FeatureDiscoveryInfo d{};d.SDKVersion=NVSDK_NGX_Version_API;
    d.FeatureID=NVSDK_NGX_Feature_SuperSampling;
    d.Identifier.IdentifierType=NVSDK_NGX_Application_Identifier_Type_Project_Id;
    d.Identifier.v.ProjectDesc={PROJECT,NVSDK_NGX_ENGINE_TYPE_CUSTOM,"Viewpoint Linux local adapter"};
    d.ApplicationDataPath=cachePath.c_str();d.FeatureInfo=&common;return d;
}
void close(){
    if(device)vkDeviceWaitIdle(device);
    if(feature){NVSDK_NGX_VULKAN_ReleaseFeature(feature);feature=nullptr;}
    if(params){NVSDK_NGX_VULKAN_DestroyParameters(params);params=nullptr;}
    if(initialized){NVSDK_NGX_VULKAN_Shutdown1(device);initialized=false;}
    device=VK_NULL_HANDLE;
}
}
#define API extern "C" __attribute__((visibility("default")))
API const char* vp_error(){return error.c_str();}
API int vp_abi(){return 1;}
API int vp_prepare(const char* libraries,const char* cache){return guarded([&]{
    if(!libraries||!cache)throw std::runtime_error("null library/cache path");
    if(initialized)throw std::runtime_error("NGX already initialized");
    libraryPath=std::filesystem::path(libraries).wstring();cachePath=std::filesystem::path(cache).wstring();
    searchPath=libraryPath.c_str();common={};common.PathListInfo.Path=&searchPath;common.PathListInfo.Length=1;
});}
API const char* vp_extensions(int kind,VkInstance instance,VkPhysicalDevice physical){
    int rc=guarded([&]{
        auto d=discovery();uint32_t count=0;VkExtensionProperties* properties=nullptr;
        if(kind==0)ngx(NVSDK_NGX_VULKAN_GetFeatureInstanceExtensionRequirements(&d,&count,&properties),"instance extensions");
        else ngx(NVSDK_NGX_VULKAN_GetFeatureDeviceExtensionRequirements(instance,physical,&d,&count,&properties),"device extensions");
        extensions.clear();for(uint32_t i=0;i<count;i++){extensions+=properties[i].extensionName;extensions+='\n';}
    });
    return rc==0?extensions.c_str():nullptr;
}
API int vp_open(VkInstance instance,VkPhysicalDevice physical,VkDevice dev,VkQueue queue,
                int family,int iw,int ih,int ow,int oh,int quality){return guarded([&]{
    if(initialized)throw std::runtime_error("only one NGX viewport is supported");
    if(!instance||!physical||!dev||!queue||iw<=0||ih<=0||ow<=0||oh<=0)throw std::runtime_error("invalid Vulkan context/dimensions");
    device=dev;
    try {
        ngx(NVSDK_NGX_VULKAN_Init_with_ProjectID(PROJECT,NVSDK_NGX_ENGINE_TYPE_CUSTOM,"Viewpoint Linux local adapter",
            cachePath.c_str(),instance,physical,device,vkGetInstanceProcAddr,vkGetDeviceProcAddr,&common),"NGX Init");
        initialized=true;ngx(NVSDK_NGX_VULKAN_GetCapabilityParameters(&params),"capabilities");
        int available=0;ngx(params->Get(NVSDK_NGX_Parameter_SuperSampling_Available,&available),"DLSS availability");
        if(!available)throw std::runtime_error("NGX reports DLSS unavailable on this Vulkan device");
        NVSDK_NGX_DLSS_Create_Params cp{};
        cp.Feature.InWidth=iw;cp.Feature.InHeight=ih;cp.Feature.InTargetWidth=ow;cp.Feature.InTargetHeight=oh;
        cp.Feature.InPerfQualityValue=static_cast<NVSDK_NGX_PerfQuality_Value>(quality);
        cp.InFeatureCreateFlags=NVSDK_NGX_DLSS_Feature_Flags_MVLowRes|NVSDK_NGX_DLSS_Feature_Flags_AutoExposure;
        VkCommandPool pool=VK_NULL_HANDLE;VkFence fence=VK_NULL_HANDLE;
        try {
            VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;
            vk(vkCreateCommandPool(device,&pi,nullptr,&pool),"create NGX command pool");
            VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
            VkCommandBuffer command;vk(vkAllocateCommandBuffers(device,&ai,&command),"allocate NGX command buffer");
            VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
            vk(vkBeginCommandBuffer(command,&bi),"begin NGX create");
            ngx(NGX_VULKAN_CREATE_DLSS_EXT1(device,command,1,1,&feature,params,&cp),"create DLSS");
            vk(vkEndCommandBuffer(command),"end NGX create");
            VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};vk(vkCreateFence(device,&fi,nullptr,&fence),"create NGX fence");
            VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;
            vk(vkQueueSubmit(queue,1,&si,fence),"submit NGX create");
            vk(vkWaitForFences(device,1,&fence,VK_TRUE,UINT64_MAX),"wait NGX create");
            vkDestroyFence(device,fence,nullptr);vkDestroyCommandPool(device,pool,nullptr);
        }catch(...){vkDeviceWaitIdle(device);if(fence)vkDestroyFence(device,fence,nullptr);if(pool)vkDestroyCommandPool(device,pool,nullptr);throw;}
        inWidth=iw;inHeight=ih;firstFrame=true;
    }catch(...){close();throw;}
});}
// Four resource records: image, view, format, width, height (all uint64_t).
API int vp_record(VkCommandBuffer command,const uint64_t* resources,float jx,float jy,float mx,float my,float frameMs,int reset){return guarded([&]{
    if(!feature||!command||!resources)throw std::runtime_error("DLSS context or resources missing");
    NVSDK_NGX_Resource_VK images[4]{};
    for(int i=0;i<4;i++){
        const auto* p=resources+i*5;
        if(!p[0]||!p[1]||!p[3]||!p[4])throw std::runtime_error("invalid DLSS image");
        VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        images[i]=NVSDK_NGX_Create_ImageView_Resource_VK(reinterpret_cast<VkImageView>(p[1]),reinterpret_cast<VkImage>(p[0]),range,static_cast<VkFormat>(p[2]),p[3],p[4],i==3);
    }
    // Viewpoint's external ownership crossings keep every image in GENERAL.
    // NGX requires read-only layouts for its inputs. Restore GENERAL afterwards.
    VkImageMemoryBarrier barriers[3]{};
    for(int i=0;i<3;i++){
        auto& b=barriers[i];b.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        b.srcAccessMask=VK_ACCESS_MEMORY_WRITE_BIT|VK_ACCESS_MEMORY_READ_BIT;
        b.dstAccessMask=VK_ACCESS_SHADER_READ_BIT;
        b.oldLayout=VK_IMAGE_LAYOUT_GENERAL;b.newLayout=VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        b.srcQueueFamilyIndex=b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        b.image=images[i].Resource.ImageViewInfo.Image;b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
    }
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,0,nullptr,0,nullptr,3,barriers);
    NVSDK_NGX_VK_DLSS_Eval_Params ep{};
    ep.Feature.pInColor=&images[0];ep.pInDepth=&images[1];ep.pInMotionVectors=&images[2];ep.Feature.pInOutput=&images[3];
    ep.InJitterOffsetX=jx;ep.InJitterOffsetY=jy;ep.InMVScaleX=mx;ep.InMVScaleY=my;
    ep.InFrameTimeDeltaInMsec=frameMs;ep.InReset=reset||firstFrame;ep.InRenderSubrectDimensions={inWidth,inHeight};
    ngx(NGX_VULKAN_EVALUATE_DLSS_EXT(command,feature,params,&ep),"evaluate DLSS");
    firstFrame=false;
    for(auto& b:barriers){b.srcAccessMask=VK_ACCESS_SHADER_READ_BIT;b.dstAccessMask=VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT;
        b.oldLayout=VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;b.newLayout=VK_IMAGE_LAYOUT_GENERAL;}
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,0,0,nullptr,0,nullptr,3,barriers);
});}
API int vp_close(){return guarded([]{close();});}
