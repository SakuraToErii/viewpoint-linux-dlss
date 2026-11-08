package viewpoint.upscale;
import java.util.List;
import org.lwjgl.opengl.GL11;
import org.lwjgl.vulkan.*;

/** Linux NGX frame generation, using Viewpoint's existing two-frame presenter. */
public final class FrameGeneration implements AutoCloseable {
    public static final NativeFiles.Set FILES=NativeFiles.Set.DLSS;
    public final int screenWidth,screenHeight,frameWidth,frameHeight;
    private final VulkanDevice vk;
    private final Crossing crossing;
    private final Images images;
    private final SharedImage[] all;
    private final LinuxFrameNgx ngx;
    private boolean closed;
    private FrameGeneration(int sw,int sh,int rw,int rh) {
        screenWidth=sw;screenHeight=sh;frameWidth=rw;frameHeight=rh;
        LinuxFrameNgx newNgx=null;VulkanDevice newVk=null;Crossing newCrossing=null;
        SharedImage[] created=new SharedImage[5];boolean opened=false;
        try {
            newNgx=new LinuxFrameNgx();
            LinuxFrameNgx backend=newNgx;
            newVk=VulkanDevice.open(new VulkanDevice.Needs(){
                public List<String> instanceExtensions(){return backend.extensions(0,0,0);}
                public List<String> deviceExtensions(VkInstance i,VkPhysicalDevice p){return backend.extensions(1,i.address(),p.address());}
            });
            newCrossing=new Crossing(newVk);
            newNgx.open(newVk,rw,rh,sw,sh);opened=true;
            created[0]=new SharedImage(newVk,37,32856,sw,sh);
            created[1]=new SharedImage(newVk,37,32856,sw,sh);
            created[2]=new SharedImage(newVk,37,32856,sw,sh);
            created[3]=new SharedImage(newVk,100,33326,rw,rh);
            created[4]=new SharedImage(newVk,83,33327,rw,rh);
            GL11.glFinish();
            vk=newVk;crossing=newCrossing;ngx=newNgx;all=created;
            images=new Images(created[0],created[1],created[2],created[3],created[4]);
            System.out.println("[Viewpoint Linux DLSSG] NGX initialized: "+sw+"x"+sh+", guides "+rw+"x"+rh+", 2x");
        } catch(RuntimeException|Error failure) {
            if(newVk!=null)try{newVk.idle();}catch(Throwable cleanup){failure.addSuppressed(cleanup);}
            if(opened)try{newNgx.close();}catch(Throwable cleanup){failure.addSuppressed(cleanup);}
            cleanup(newCrossing,failure);for(SharedImage image:created)cleanup(image,failure);cleanup(newVk,failure);
            throw failure;
        }
    }
    private static void cleanup(AutoCloseable resource,Throwable failure){
        if(resource!=null)try{resource.close();}catch(Throwable cleanup){failure.addSuppressed(cleanup);}
    }
    public static String unsupported(){
        String interop=VulkanDevice.unavailable();
        return interop!=null?interop:DlssVendor.unavailable();
    }
    public static String unavailable(){
        String reason=unsupported();
        return reason!=null?reason:NativeFiles.ready(FILES)?null:"Linux DLSS frame-generation libraries are missing";
    }
    public static FrameGeneration open(int sw,int sh,int rw,int rh){
        String reason=unavailable();
        if(reason!=null)throw new IllegalStateException("frame generation cannot run: "+reason);
        return new FrameGeneration(sw,sh,rw,rh);
    }
    public int screen(){return images.screen().texture;}
    public int hudless(){return images.hudless().texture;}
    public int generated(){return images.generated().texture;}
    public int depth(){return images.depth().texture;}
    public int motion(){return images.motion().texture;}
    public void generate(UpscaleFrame frame,boolean reset){
        crossing.handOver(all);
        VkCommandBuffer command=vk.begin();crossing.acquire(command,all);
        ngx.record(command.address(),images,frame,reset);
        crossing.release(command,all);crossing.submit(command);crossing.takeBack(all);
    }
    public void close(){
        if(closed)return;closed=true;GL11.glFinish();vk.idle();ngx.close();crossing.close();
        for(SharedImage image:all)image.close();vk.close();
    }
    record Images(SharedImage screen,SharedImage hudless,SharedImage generated,SharedImage depth,SharedImage motion){
        SharedImage[] all(){return new SharedImage[]{screen,hudless,generated,depth,motion};}
    }
}
