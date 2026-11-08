package viewpoint.upscale;
import org.lwjgl.glfw.*;
import org.lwjgl.opengl.*;
import java.nio.file.*;

/** Hidden-context integration test; no game initialization, saves or mod approvals. */
public final class GpuNgxTest {
    private static void clear(int texture,int format,float[] value){
        GL44.glClearTexImage(texture,0,format,GL11.GL_FLOAT,value);
    }
    private static long fds()throws Exception{
        try(var paths=Files.list(Path.of("/proc/self/fd"))){return paths.count();}
    }
    public static void main(String[] args)throws Exception{
        GLFWErrorCallback errors=GLFWErrorCallback.createPrint(System.err);GLFW.glfwSetErrorCallback(errors);
        if(!GLFW.glfwInit())throw new IllegalStateException("GLFW init failed");
        GLFW.glfwWindowHint(GLFW.GLFW_VISIBLE,GLFW.GLFW_FALSE);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MAJOR,4);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MINOR,5);
        long window=GLFW.glfwCreateWindow(32,32,"Viewpoint Linux DLSS hidden test",0,0);
        if(window==0)throw new IllegalStateException("hidden GL context failed");
        try{
            GLFW.glfwMakeContextCurrent(window);GL.createCapabilities();
            System.out.println("GL renderer: "+GL11.glGetString(GL11.GL_RENDERER));
            System.out.println("GL version: "+GL11.glGetString(GL11.GL_VERSION));
            System.out.println("FD memory: "+GL.getCapabilities().GL_EXT_memory_object_fd+", semaphore: "+GL.getCapabilities().GL_EXT_semaphore_fd);
            long baseline=fds();
            for(int cycle=0;cycle<3;cycle++){
                int width=128+cycle*32,height=128+cycle*32;
                try(Upscaling up=Upscaling.open(Upscaling.Kind.DLSS,67,width,height)){
                    clear(up.color(),GL11.GL_RGBA,new float[]{0.2f,0.4f,0.6f,1f});
                    clear(up.depth(),GL11.GL_RED,new float[]{0.5f});
                    clear(up.motion(),GL30.GL_RG,new float[]{0f,0f});
                    clear(up.output(),GL11.GL_RGBA,new float[]{1f,0f,1f,1f});
                    VulkanDevice.glCheck("fill test input");
                    for(int frame=0;frame<4;frame++){
                        up.run(new UpscaleFrame(0f,0f,up.frameWidth,up.frameHeight,frame==0,16.67f,0.05f,400f,1.0f,1f,new float[64],new float[12]));
                    }
                    GL11.glFinish();
                    float[] output=new float[width*height*4];
                    GL11.glBindTexture(GL11.GL_TEXTURE_2D,up.output());
                    GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,output);
                    VulkanDevice.glCheck("read DLSS output");
                    for(float value:output)if(!Float.isFinite(value))throw new AssertionError("nonfinite DLSS output");
                    int pixel=(height/2*width+width/2)*4;
                    float r=output[pixel],g=output[pixel+1],b=output[pixel+2];
                    System.out.println("Cycle "+cycle+": center RGB = "+r+", "+g+", "+b);
                    if(Math.abs(r-0.2f)>0.15f||Math.abs(g-0.4f)>0.15f||Math.abs(b-0.6f)>0.15f)
                        throw new AssertionError("DLSS output is not the constant input color");
                }
                GL11.glFinish();GLFW.glfwPollEvents();
                System.out.println("Cycle "+cycle+" closed; FD count "+fds());
                java.util.Map<String,Integer> descriptorTypes=new java.util.TreeMap<>();
                try(var paths=Files.list(Path.of("/proc/self/fd"))){
                    paths.forEach(path->{try{String name=Files.readSymbolicLink(path).toString();
                        if(name.startsWith("/dev/")||name.startsWith("anon_inode"))descriptorTypes.merge(name,1,Integer::sum);
                    }catch(Exception ignored){}});
                }
                System.out.println("Driver descriptors: "+descriptorTypes);
            }
            System.out.println("PASS: FD sharing, NGX initialization, DLSS GPU evaluation, output readback and recreate/teardown. FDs: "+baseline+" -> "+fds());
        }finally{
            GLFW.glfwMakeContextCurrent(0);GLFW.glfwDestroyWindow(window);GLFW.glfwTerminate();errors.free();
            System.out.println("FD count after destroying GL context: "+fds());
        }
    }
}
