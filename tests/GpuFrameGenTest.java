package viewpoint.upscale;
import org.lwjgl.glfw.*;
import org.lwjgl.opengl.*;
import org.joml.Matrix4f;

/** Proves interpolation differs from the current frame, rather than counting duplicates as generated frames. */
public final class GpuFrameGenTest {
    private static int WIDTH=512,HEIGHT=512;
    private static void clear(int texture,int format,float[] value){GL44.glClearTexImage(texture,0,format,GL11.GL_FLOAT,value);}
    private static void upload(int texture,int format,float[] pixels){
        upload(texture,format,pixels,WIDTH,HEIGHT);
    }
    private static void upload(int texture,int format,float[] pixels,int width,int height){
        GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
        GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,width,height,format,GL11.GL_FLOAT,pixels);
    }
    private static double centroid(float[] pixels){
        double total=0,weighted=0;
        for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++){
            int p=(y*WIDTH+x)*4;float r=pixels[p],g=pixels[p+1],b=pixels[p+2];
            if(!Float.isFinite(r)||!Float.isFinite(g)||!Float.isFinite(b))throw new AssertionError("nonfinite interpolation");
            double weight=Math.max(0,r-g-0.12f);
            total+=weight;weighted+=weight*x;
        }
        if(total<100)throw new AssertionError("moving object missing from generated frame");
        return weighted/total;
    }
    private static UpscaleFrame frame(boolean reset){
        float[] matrices=new float[64];
        Matrix4f projection=new Matrix4f().perspective(1f,(float)WIDTH/HEIGHT,0.05f,400f);
        projection.get(matrices,0);new Matrix4f(projection).invert().get(matrices,16);
        new Matrix4f().get(matrices,32);new Matrix4f().get(matrices,48);
        float[] camera={0,0,0,0,1,0,1,0,0,0,0,-1};
        return new UpscaleFrame(0,0,WIDTH,HEIGHT,reset,16.67f,0.05f,400f,1f,1f,matrices,camera);
    }
    public static void main(String[] args){
        if(args.length>=2){WIDTH=Integer.parseInt(args[0]);HEIGHT=Integer.parseInt(args[1]);}
        int guideWidth=Math.round(WIDTH*0.67f),guideHeight=Math.round(HEIGHT*0.67f);
        GLFWErrorCallback errors=GLFWErrorCallback.createPrint(System.err);GLFW.glfwSetErrorCallback(errors);
        if(!GLFW.glfwInit())throw new IllegalStateException("GLFW init failed");
        GLFW.glfwWindowHint(GLFW.GLFW_VISIBLE,GLFW.GLFW_FALSE);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MAJOR,4);GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MINOR,5);
        long window=GLFW.glfwCreateWindow(32,32,"Viewpoint DLSSG hidden test",0,0);
        if(window==0)throw new IllegalStateException("GL context failed");
        try{
            GLFW.glfwMakeContextCurrent(window);GL.createCapabilities();
            System.out.println("GL renderer: "+GL11.glGetString(GL11.GL_RENDERER));
            // Keep Super Resolution alive while frame generation initializes and runs.
            // This exercises independent SDK contexts and alternating per-frame calls.
            try(Upscaling sr=Upscaling.open(Upscaling.Kind.DLSS,67,WIDTH,HEIGHT);
                FrameGeneration fg=FrameGeneration.open(WIDTH,HEIGHT,guideWidth,guideHeight)){
                clear(sr.color(),GL11.GL_RGBA,new float[]{0.2f,0.4f,0.6f,1});
                clear(sr.depth(),GL11.GL_RED,new float[]{0.5f});clear(sr.motion(),GL30.GL_RG,new float[]{0,0});
                int interpolated=0;
                for(int i=0;i<12;i++){
                    int cx=160+i*6;
                    float[] color=new float[WIDTH*HEIGHT*4],depth=new float[guideWidth*guideHeight],motion=new float[guideWidth*guideHeight*2];
                    for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++){
                        int pixel=y*WIDTH+x;boolean object=Math.abs(x-cx)<48&&Math.abs(y-HEIGHT/2)<48;
                        color[pixel*4]=object?0.9f:0.05f;color[pixel*4+1]=object?0.12f:0.05f;
                        color[pixel*4+2]=0.05f;color[pixel*4+3]=1f;
                    }
                    for(int y=0;y<guideHeight;y++)for(int x=0;x<guideWidth;x++){
                        int pixel=y*guideWidth+x;
                        boolean object=Math.abs(x*(float)WIDTH/guideWidth-cx)<48&&Math.abs(y*(float)HEIGHT/guideHeight-HEIGHT/2)<48;
                        depth[pixel]=object?0.2f:0.5f;if(object)motion[pixel*2]=-6f/WIDTH;
                    }
                    upload(fg.screen(),GL11.GL_RGBA,color);upload(fg.hudless(),GL11.GL_RGBA,color);
                    upload(fg.depth(),GL11.GL_RED,depth,guideWidth,guideHeight);upload(fg.motion(),GL30.GL_RG,motion,guideWidth,guideHeight);
                    VulkanDevice.glCheck("upload DLSSG motion fixture");
                    sr.run(frame(i==0));fg.generate(frame(i==0),i==0);
                    GL11.glFinish();float[] output=new float[color.length];
                    GL11.glBindTexture(GL11.GL_TEXTURE_2D,fg.generated());
                    GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,output);
                    VulkanDevice.glCheck("read generated output");
                    double generated=centroid(output),real=centroid(color),lag=real-generated;
                    System.out.printf(java.util.Locale.ROOT,"Frame %d: current=%.3f generated=%.3f lag=%.3f (midpoint lag 3)\n",i,real,generated,lag);
                    if(i>=4&&lag>0.6&&lag<5.4)interpolated++;
                }
                if(interpolated<4)throw new AssertionError("No reliable midpoint interpolation: "+interpolated+"/8; current-frame duplicates do not count");
                System.out.println("PASS: SR and FG coexist; moving-object output differs from current frames and lies between consecutive frame positions.");
            }
        }finally{GLFW.glfwMakeContextCurrent(0);GLFW.glfwDestroyWindow(window);GLFW.glfwTerminate();errors.free();}
    }
}
