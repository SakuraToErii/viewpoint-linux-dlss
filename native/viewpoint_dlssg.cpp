// Private local Linux NGX frame-generation adapter; one intermediate frame.
#include <vulkan/vulkan.h>
#include "nvsdk_ngx.h"
#include "nvsdk_ngx_vk.h"
#include "nvsdk_ngx_helpers_vk.h"
#include "nvsdk_ngx_helpers_dlssg_vk.h"
#include "ngx_worker.h"
#include <filesystem>
#include <string>
#include <cstring>
#include <cstdio>
#include <limits>

namespace {
std::string error, extensionNames;
std::wstring libraryPath,cachePath;
const wchar_t* searchPath=nullptr;
NVSDK_NGX_FeatureCommonInfo common{};
constexpr const char* PROJECT="3c3a1ca4-cbca-4eda-9170-e1b3bb2e61a1";
VkDevice device=VK_NULL_HANDLE;
NVSDK_NGX_Parameter* params=nullptr;
NVSDK_NGX_Handle* feature=nullptr;
bool initialized=false,firstFrame=true;
unsigned screenWidth=0,screenHeight=0,renderWidth=0,renderHeight=0;
void ngx(NVSDK_NGX_Result r,const char* operation){if(NVSDK_NGX_FAILED(r)){
    char b[180];snprintf(b,sizeof b,"%s failed: NGX 0x%08x",operation,unsigned(r));throw std::runtime_error(b);}}
void vk(VkResult r,const char* operation){if(r!=VK_SUCCESS)throw std::runtime_error(std::string(operation)+": "+std::to_string(r));}
template<class F> int guarded(F fn){try{worker().run(fn);error.clear();return 0;}catch(const std::exception& e){error=e.what();return -1;}}
NVSDK_NGX_FeatureDiscoveryInfo discovery(){
    NVSDK_NGX_FeatureDiscoveryInfo d{};d.SDKVersion=NVSDK_NGX_Version_API;d.FeatureID=NVSDK_NGX_Feature_FrameGeneration;
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
API int vp_abi(){return 2;}
API const char* vp_error(){return error.c_str();}
API int vp_prepare(const char* libraries,const char* cache){return guarded([&]{
    if(!libraries||!cache)throw std::runtime_error("null library/cache path");
    if(initialized)throw std::runtime_error("DLSSG already initialized");
    libraryPath=std::filesystem::path(libraries).wstring();cachePath=std::filesystem::path(cache).wstring();
    searchPath=libraryPath.c_str();common={};common.PathListInfo.Path=&searchPath;common.PathListInfo.Length=1;
});}
API const char* vp_extensions(int kind,VkInstance instance,VkPhysicalDevice physical){
    int rc=guarded([&]{auto d=discovery();uint32_t count=0;VkExtensionProperties* props=nullptr;
        if(kind==0)ngx(NVSDK_NGX_VULKAN_GetFeatureInstanceExtensionRequirements(&d,&count,&props),"DLSSG instance extensions");
        else ngx(NVSDK_NGX_VULKAN_GetFeatureDeviceExtensionRequirements(instance,physical,&d,&count,&props),"DLSSG device extensions");
        extensionNames.clear();for(uint32_t i=0;i<count;i++){extensionNames+=props[i].extensionName;extensionNames+='\n';}});
    return rc==0?extensionNames.c_str():nullptr;
}
API int vp_open(VkInstance instance,VkPhysicalDevice physical,VkDevice dev,VkQueue queue,
                int family,int rw,int rh,int sw,int sh){return guarded([&]{
    if(initialized)throw std::runtime_error("only one DLSSG viewport is supported");
    if(!instance||!physical||!dev||!queue||rw<=0||rh<=0||sw<=0||sh<=0)throw std::runtime_error("invalid DLSSG Vulkan context/dimensions");
    device=dev;
    try{
        ngx(NVSDK_NGX_VULKAN_Init_with_ProjectID(PROJECT,NVSDK_NGX_ENGINE_TYPE_CUSTOM,"Viewpoint Linux local adapter",
            cachePath.c_str(),instance,physical,device,vkGetInstanceProcAddr,vkGetDeviceProcAddr,&common),"DLSSG NGX init");
        initialized=true;ngx(NVSDK_NGX_VULKAN_GetCapabilityParameters(&params),"DLSSG capabilities");
        int available=0;ngx(params->Get(NVSDK_NGX_Parameter_FrameGeneration_Available,&available),"frame-generation availability");
        if(!available)throw std::runtime_error("NGX reports frame generation unavailable on this device/driver");
        params->Set(NVSDK_NGX_Parameter_CreationNodeMask,1u);params->Set(NVSDK_NGX_Parameter_VisibilityNodeMask,1u);
        params->Set(NVSDK_NGX_Parameter_Width,unsigned(sw));params->Set(NVSDK_NGX_Parameter_Height,unsigned(sh));
        params->Set(NVSDK_NGX_DLSSG_Parameter_Width,unsigned(sw));params->Set(NVSDK_NGX_DLSSG_Parameter_Height,unsigned(sh));
        params->Set(NVSDK_NGX_DLSSG_Parameter_BackbufferFormat,unsigned(VK_FORMAT_R8G8B8A8_UNORM));
        params->Set(NVSDK_NGX_DLSSG_Parameter_InternalWidth,unsigned(rw));params->Set(NVSDK_NGX_DLSSG_Parameter_InternalHeight,unsigned(rh));
        params->Set(NVSDK_NGX_DLSSG_Parameter_DynamicResolution,0u);
        params->Set(NVSDK_NGX_DLSSG_Parameter_ResourceAlwaysProvided_Flags,
            unsigned(NVSDK_NGX_DLSSG_ResourceFlags_Backbuffer|NVSDK_NGX_DLSSG_ResourceFlags_MVecs|NVSDK_NGX_DLSSG_ResourceFlags_Depth|
                     NVSDK_NGX_DLSSG_ResourceFlags_HUDLess|NVSDK_NGX_DLSSG_ResourceFlags_OutputInterpolated));
        params->Set(NVSDK_NGX_DLSSG_Parameter_ResourceNeverProvided_Flags,
            unsigned(NVSDK_NGX_DLSSG_ResourceFlags_UI|NVSDK_NGX_DLSSG_ResourceFlags_UIAlpha|
                     NVSDK_NGX_DLSSG_ResourceFlags_BidirectionalDistortionField|NVSDK_NGX_DLSSG_ResourceFlags_OutputReal));
        VkCommandPool pool=VK_NULL_HANDLE;VkFence fence=VK_NULL_HANDLE;
        try{
            VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;
            vk(vkCreateCommandPool(device,&pi,nullptr,&pool),"DLSSG create command pool");
            VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
            VkCommandBuffer cmd;vk(vkAllocateCommandBuffers(device,&ai,&cmd),"DLSSG allocate command buffer");
            VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
            vk(vkBeginCommandBuffer(cmd,&bi),"DLSSG begin creation");
            ngx(NVSDK_NGX_VULKAN_CreateFeature1(device,cmd,NVSDK_NGX_Feature_FrameGeneration,params,&feature),"DLSSG create feature");
            vk(vkEndCommandBuffer(cmd),"DLSSG end creation");
            VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};vk(vkCreateFence(device,&fi,nullptr,&fence),"DLSSG create fence");
            VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&cmd;
            vk(vkQueueSubmit(queue,1,&si,fence),"DLSSG submit creation");
            vk(vkWaitForFences(device,1,&fence,VK_TRUE,UINT64_MAX),"DLSSG wait creation");
            vkDestroyFence(device,fence,nullptr);vkDestroyCommandPool(device,pool,nullptr);
        }catch(...){vkDeviceWaitIdle(device);if(fence)vkDestroyFence(device,fence,nullptr);if(pool)vkDestroyCommandPool(device,pool,nullptr);throw;}
        screenWidth=sw;screenHeight=sh;renderWidth=rw;renderHeight=rh;firstFrame=true;
    }catch(...){close();throw;}
});}
// Five resource records: screen, hudless, generated, depth, motion.
// Each resource is [image, imageView, VkFormat, width, height], uint64_t.
// Constants: four converted column-major matrices (64 floats), camera (12),
// jitter XY, near, far, vertical FOV, aspect (6). Column-major column-vector
// matrices have the same storage as row-major row-vector matrices in NGX.
API int vp_record(VkCommandBuffer command,const uint64_t* records,const float* c,int reset){return guarded([&]{
    if(!feature||!command||!records||!c)throw std::runtime_error("DLSSG context/resources/constants missing");
    NVSDK_NGX_Resource_VK images[5]{};
    for(int i=0;i<5;i++){
        const auto* p=records+i*5;if(!p[0]||!p[1]||!p[3]||!p[4])throw std::runtime_error("invalid DLSSG image");
        VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        images[i]=NVSDK_NGX_Create_ImageView_Resource_VK(reinterpret_cast<VkImageView>(p[1]),reinterpret_cast<VkImage>(p[0]),range,static_cast<VkFormat>(p[2]),p[3],p[4],i==2);
    }
    // Seed the output with the real frame: if interpolation is suppressed by the
    // SDK, Viewpoint can never display uninitialized or stale generated pixels.
    VkImageMemoryBarrier copyBarriers[2]{};
    for(int i=0;i<2;i++){auto& b=copyBarriers[i];b.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        b.srcAccessMask=VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT;
        b.dstAccessMask=i==0?VK_ACCESS_TRANSFER_READ_BIT:VK_ACCESS_TRANSFER_WRITE_BIT;
        b.oldLayout=b.newLayout=VK_IMAGE_LAYOUT_GENERAL;b.srcQueueFamilyIndex=b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        b.image=images[i==0?0:2].Resource.ImageViewInfo.Image;b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};}
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,2,copyBarriers);
    VkImageCopy region{};region.srcSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};region.dstSubresource=region.srcSubresource;region.extent={screenWidth,screenHeight,1};
    vkCmdCopyImage(command,images[0].Resource.ImageViewInfo.Image,VK_IMAGE_LAYOUT_GENERAL,
        images[2].Resource.ImageViewInfo.Image,VK_IMAGE_LAYOUT_GENERAL,1,&region);
    auto outputBarrier=copyBarriers[1];outputBarrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
    outputBarrier.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,0,0,nullptr,0,nullptr,1,&outputBarrier);
    // NGX readers expect SHADER_READ_ONLY; Viewpoint's GL/VK crossings use GENERAL.
    int inputs[]={0,1,3,4};VkImageMemoryBarrier barriers[4]{};
    for(int i=0;i<4;i++){auto& b=barriers[i];b.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        b.srcAccessMask=VK_ACCESS_MEMORY_WRITE_BIT|VK_ACCESS_MEMORY_READ_BIT;b.dstAccessMask=VK_ACCESS_SHADER_READ_BIT;
        b.oldLayout=VK_IMAGE_LAYOUT_GENERAL;b.newLayout=VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        b.srcQueueFamilyIndex=b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        b.image=images[inputs[i]].Resource.ImageViewInfo.Image;b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};}
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,0,0,nullptr,0,nullptr,4,barriers);
    NVSDK_NGX_VK_DLSSG_Eval_Params ep{};ep.pBackbuffer=&images[0];ep.pHudless=&images[1];ep.pOutputInterpFrame=&images[2];ep.pDepth=&images[3];ep.pMVecs=&images[4];
    NVSDK_NGX_DLSSG_Opt_Eval_Params op{};
    std::memcpy(op.cameraViewToClip,c,64);std::memcpy(op.clipToCameraView,c+16,64);
    std::memcpy(op.clipToPrevClip,c+32,64);std::memcpy(op.prevClipToClip,c+48,64);
    for(int i=0;i<4;i++)op.clipToLensClip[i][i]=1.f;
    std::memcpy(op.cameraPos,c+64,12);std::memcpy(op.cameraUp,c+67,12);
    std::memcpy(op.cameraRight,c+70,12);std::memcpy(op.cameraFwd,c+73,12);
    op.jitterOffset[0]=c[76];op.jitterOffset[1]=c[77];op.mvecScale[0]=op.mvecScale[1]=1.f;
    op.cameraNear=c[78];op.cameraFar=c[79];op.cameraFOV=c[80];op.cameraAspectRatio=c[81];
    op.depthInverted=false;op.cameraMotionIncluded=true;op.reset=reset||firstFrame;op.colorBuffersHDR=false;
    op.motionVectorsInvalidValue=std::numeric_limits<float>::max();op.motionVectorsDilated=false;
    op.multiFrameCount=op.multiFrameIndex=1;
    op.mvecsSubrectSize=op.depthSubrectSize={renderWidth,renderHeight};
    op.hudLessSubrectSize=op.backbufferSubrectSize=op.outputInterpSubrectSize={screenWidth,screenHeight};
    ngx(NGX_VK_EVALUATE_DLSSG(command,feature,params,&ep,&op),"DLSSG evaluate feature");firstFrame=false;
    for(auto& b:barriers){b.srcAccessMask=VK_ACCESS_SHADER_READ_BIT;b.dstAccessMask=VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT;
        b.oldLayout=VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;b.newLayout=VK_IMAGE_LAYOUT_GENERAL;}
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,0,0,nullptr,0,nullptr,4,barriers);
});}
API int vp_close(){return guarded([]{close();});}
