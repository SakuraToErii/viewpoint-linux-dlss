package viewpoint.upscale;
import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;
import java.nio.file.Path;
import static java.lang.foreign.ValueLayout.*;
public final class OfflineNgxTest {
    public static void main(String[] args) throws Throwable {
        if (!NativeFiles.ready(NativeFiles.Set.DLSS)) throw new AssertionError("manifest cannot find staged Linux libraries");
        if (!Upscaling.Kind.FSR3.unsupported().contains("DLSS Super Resolution only")) throw new AssertionError("FSR falsely enabled");
        if (!Upscaling.Kind.XESS.unsupported().contains("DLSS Super Resolution only")) throw new AssertionError("XeSS falsely enabled");
        testCameraConstants();
        LinuxFrameNgx fg = new LinuxFrameNgx();
        fg.close();
        testFrameGenAbi(Path.of(args[0]).resolveSibling("libviewpoint_dlssg.so"));
        LinuxNgx ngx = new LinuxNgx();
        // Preparation and close do not call Vulkan/NGX initialization.
        ngx.close();
        SymbolLookup lib=SymbolLookup.libraryLookup(Path.of(args[0]),Arena.global());
        MethodHandle open=Linker.nativeLinker().downcallHandle(lib.find("vp_open").orElseThrow(),
            FunctionDescriptor.of(JAVA_INT,ADDRESS,ADDRESS,ADDRESS,ADDRESS,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT));
        int result=(int)open.invokeExact(MemorySegment.NULL,MemorySegment.NULL,MemorySegment.NULL,MemorySegment.NULL,0,0,0,0,0,0);
        if(result!=-1)throw new AssertionError("invalid context was accepted");
        MethodHandle error=Linker.nativeLinker().downcallHandle(lib.find("vp_error").orElseThrow(),FunctionDescriptor.of(ADDRESS));
        String message=((MemorySegment)error.invokeExact()).reinterpret(16384).getString(0);
        if(!message.contains("invalid Vulkan context"))throw new AssertionError(message);
        ngx.close();
        for(String name:new String[]{"VulkanDevice","Crossing","SharedImage","DlssVendor","DlssVendor$1","LinuxNgx","LinuxFrameNgx","FrameGenConstants","FrameGeneration","FrameGeneration$1"}){
            Class<?> c=Class.forName("viewpoint.upscale."+name,false,OfflineNgxTest.class.getClassLoader());
            c.getDeclaredMethods();c.getDeclaredConstructors();c.getDeclaredFields();
        }
        System.out.println("PASS: Linux SR/FG manifests, both FFM ABIs, camera depth/Y mapping and inverse transforms, invalid-context rejection, JVM verification. No GPU work submitted.");
    }
    private static void testFrameGenAbi(Path path)throws Throwable{
        SymbolLookup lib=SymbolLookup.libraryLookup(path,Arena.global());
        MethodHandle open=Linker.nativeLinker().downcallHandle(lib.find("vp_open").orElseThrow(),
            FunctionDescriptor.of(JAVA_INT,ADDRESS,ADDRESS,ADDRESS,ADDRESS,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT));
        int result=(int)open.invokeExact(MemorySegment.NULL,MemorySegment.NULL,MemorySegment.NULL,MemorySegment.NULL,0,0,0,0,0);
        if(result!=-1)throw new AssertionError("DLSSG accepted invalid Vulkan context");
        MethodHandle error=Linker.nativeLinker().downcallHandle(lib.find("vp_error").orElseThrow(),FunctionDescriptor.of(ADDRESS));
        String message=((MemorySegment)error.invokeExact()).reinterpret(16384).getString(0);
        if(!message.contains("invalid DLSSG Vulkan context"))throw new AssertionError(message);
    }
    private static void near(float a,float b){if(Math.abs(a-b)>0.0001f)throw new AssertionError(a+" != "+b);}
    private static void testCameraConstants(){
        float[] matrices=new float[64];
        org.joml.Matrix4f projection=new org.joml.Matrix4f().perspective(1f,2f,0.1f,100f);
        projection.get(matrices,0);new org.joml.Matrix4f(projection).invert().get(matrices,16);
        org.joml.Matrix4f previous=new org.joml.Matrix4f().translation(0.25f,0.1f,0.05f);
        previous.get(matrices,32);new org.joml.Matrix4f(previous).invert().get(matrices,48);
        float[] packed=FrameGenConstants.pack(new UpscaleFrame(0f,0f,400f,200f,true,16f,0.1f,100f,1f,1f,matrices,new float[12]),400,200);
        org.joml.Matrix4f p=new org.joml.Matrix4f().set(java.util.Arrays.copyOfRange(packed,0,16));
        org.joml.Vector4f n=p.transform(new org.joml.Vector4f(0,0,-0.1f,1));near(n.z/n.w,0f);
        org.joml.Vector4f f=p.transform(new org.joml.Vector4f(0,0,-100f,1));near(f.z/f.w,1f);
        org.joml.Vector4f top=p.transform(new org.joml.Vector4f(0,0.1f,-1f,1));
        if(top.y>=0)throw new AssertionError("image-origin Y mapping not applied");
        org.joml.Matrix4f inv=new org.joml.Matrix4f().set(java.util.Arrays.copyOfRange(packed,16,32));
        float[] identity=p.mul(inv,new org.joml.Matrix4f()).get(new float[16]);
        for(int i=0;i<16;i++)near(identity[i],i%5==0?1f:0f);
        org.joml.Matrix4f prev=new org.joml.Matrix4f().set(java.util.Arrays.copyOfRange(packed,32,48));
        org.joml.Matrix4f back=new org.joml.Matrix4f().set(java.util.Arrays.copyOfRange(packed,48,64));
        identity=prev.mul(back,new org.joml.Matrix4f()).get(new float[16]);
        for(int i=0;i<16;i++)near(identity[i],i%5==0?1f:0f);
    }
}
