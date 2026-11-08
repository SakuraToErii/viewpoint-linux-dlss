package viewpoint.upscale;
import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;
import java.nio.file.*;
import java.util.List;
import static java.lang.foreign.ValueLayout.*;

final class LinuxFrameNgx {
    private final SymbolLookup symbols;
    private final Linker linker=Linker.nativeLinker();
    private final MethodHandle prepare, extensions, open, record, close, error;
    LinuxFrameNgx(){
        Path directory=NativeFiles.folder().toPath().toAbsolutePath();
        symbols=SymbolLookup.libraryLookup(directory.resolve("libviewpoint_dlssg.so"),Arena.global());
        if((int)invoke(function("vp_abi",FunctionDescriptor.of(JAVA_INT)))!=2)
            throw new IllegalStateException("unsupported Viewpoint DLSSG bridge ABI");
        error=function("vp_error",FunctionDescriptor.of(ADDRESS));
        prepare=function("vp_prepare",FunctionDescriptor.of(JAVA_INT,ADDRESS,ADDRESS));
        extensions=function("vp_extensions",FunctionDescriptor.of(ADDRESS,JAVA_INT,ADDRESS,ADDRESS));
        open=function("vp_open",FunctionDescriptor.of(JAVA_INT,ADDRESS,ADDRESS,ADDRESS,ADDRESS,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT,JAVA_INT));
        record=function("vp_record",FunctionDescriptor.of(JAVA_INT,ADDRESS,ADDRESS,ADDRESS,JAVA_INT));
        close=function("vp_close",FunctionDescriptor.of(JAVA_INT));
        try(Arena arena=Arena.ofConfined()){
            Path cache=directory.resolve("ngx-cache-fg");Files.createDirectories(cache);
            check((int)invoke(prepare,arena.allocateFrom(directory.toString()),arena.allocateFrom(cache.toString())));
        }catch(java.io.IOException e){throw new IllegalStateException("cannot create DLSSG cache",e);}
    }
    List<String> extensions(int kind,long instance,long physical){
        MemorySegment value=(MemorySegment)invoke(extensions,kind,MemorySegment.ofAddress(instance),MemorySegment.ofAddress(physical));
        if(value.address()==0)throw failure();
        return string(value).lines().filter(s->!s.isBlank()).distinct().toList();
    }
    void open(VulkanDevice vk,int rw,int rh,int sw,int sh){
        check((int)invoke(open,MemorySegment.ofAddress(vk.instance.address()),MemorySegment.ofAddress(vk.physical.address()),
            MemorySegment.ofAddress(vk.device.address()),MemorySegment.ofAddress(vk.queue.address()),vk.family,rw,rh,sw,sh));
    }
    void record(long command,FrameGeneration.Images images,UpscaleFrame frame,boolean reset){
        try(Arena arena=Arena.ofConfined()){
            MemorySegment resources=arena.allocate(200,8);int index=0;
            for(SharedImage image:images.all())for(long value:new long[]{image.image,image.view,image.vkFormat,image.width,image.height})
                resources.setAtIndex(JAVA_LONG,index++,value);
            MemorySegment constants=arena.allocateFrom(JAVA_FLOAT,FrameGenConstants.pack(frame,images.depth().width,images.depth().height));
            check((int)invoke(record,MemorySegment.ofAddress(command),resources,constants,reset||frame.reset()?1:0));
        }
    }
    void close(){check((int)invoke(close));}
    private MethodHandle function(String name,FunctionDescriptor descriptor){
        return linker.downcallHandle(symbols.find(name).orElseThrow(()->new IllegalStateException("missing DLSSG symbol: "+name)),descriptor);
    }
    private void check(int value){if(value!=0)throw failure();}
    private IllegalStateException failure(){return new IllegalStateException("Linux DLSSG: "+string((MemorySegment)invoke(error)));}
    private static String string(MemorySegment value){return value.reinterpret(16384).getString(0);}
    private static Object invoke(MethodHandle handle,Object... values){
        try{return handle.invokeWithArguments(values);}catch(Throwable e){throw new IllegalStateException("Viewpoint Linux DLSSG call failed",e);}
    }
}
