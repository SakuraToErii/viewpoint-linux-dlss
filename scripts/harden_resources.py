"""One-time error cleanup changes to the local decompiled interop sources."""
from pathlib import Path
import sys
p=Path(sys.argv[1]).resolve()/'src/viewpoint/upscale'

f=p/'VulkanDevice.java';s=f.read_text()
for t,n in [('VkInstance','instance'),('VkPhysicalDevice','physical'),('VkDevice','device'),('VkQueue','queue')]:
    s=s.replace(f'final {t} {n};',f'{t} {n};')
s=s.replace('final int family;', 'int family;').replace('private final long pool;', 'private long pool;')
s=s.replace('    private int frame;', '    private int frame;\n    private boolean closed, loaderHeld;')
s=s.replace('''        if (onLoader++ == 0) {
            VK.create();
        }''','''        try {
        if (onLoader == 0) VK.create();
        ++onLoader;
        loaderHeld = true;''')
s=s.replace('''    public static String unavailable()''','''    public static String unavailable()''')
boundary='''    }

    public static String unavailable()'''
s=s.replace(boundary,'''        } catch (RuntimeException | Error failure) {
            try { close(); } catch (Throwable cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    public static String unavailable()''',1)
a=s.index('    @Override\n    public void close()');b=s.index('    static void closeHandle',a)
s=s[:a]+'''    @Override
    public void close() {
        if (closed) return;
        closed = true;
        if (device != null) {
            VK10.vkDeviceWaitIdle(device);
            for (long fence : fences) if (fence != 0) VK10.vkDestroyFence(device, fence, null);
            if (pool != 0) VK10.vkDestroyCommandPool(device, pool, null);
            VK10.vkDestroyDevice(device, null);
        }
        if (instance != null) VK10.vkDestroyInstance(instance, null);
        memory.free();
        if (loaderHeld && --onLoader == 0) VK.destroy();
        loaderHeld = false;
    }

'''+s[b:]
a=s.index('    static void closeHandle');b=s.index('    static void check(',a)
s=s[:a]+'''    static void closeHandle(long fd) {
        // Call this only while the application still owns the exported FD.
        if (fd >= 0) org.lwjgl.system.linux.UNISTD.close((java.nio.IntBuffer)null, Math.toIntExact(fd));
    }

    static void glCheck(String operation) {
        int error = org.lwjgl.opengl.GL11.glGetError();
        if (error != 0) throw new IllegalStateException(operation + ": GL error 0x" + Integer.toHexString(error));
    }

'''+s[b:];f.write_text(s)

f=p/'SharedImage.java';s=f.read_text()
for t,n in [('long','image'),('long','memory'),('long','view'),('int','texture'),('int','glMemory')]:
    s=s.replace(f'final {t} {n};',f'{t} {n};')
s=s.replace('private final long exported;', 'private long exported = -1;\n    private boolean closed;')
s=s.replace('''            this.exported = this.handle(memoryStack);''','''            VulkanDevice.glCheck("before Linux memory import");
            this.exported = this.handle(memoryStack);''')
line='            EXTMemoryObjectFD.glImportMemoryFdEXT((int)this.glMemory, (long)vkMemoryRequirements.size(), (int)38278, Math.toIntExact(this.exported));'
s=s.replace(line,line+'''\n            VulkanDevice.glCheck("glImportMemoryFdEXT");
            this.exported = -1; // ownership transferred to OpenGL''')
line='            GL11.glBindTexture((int)3553, (int)n5);'
s=s.replace(line,line+'\n            VulkanDevice.glCheck("shared GL texture storage");')
boundary='''        }
    }

    @Override'''
s=s.replace(boundary,'''        } catch (RuntimeException | Error failure) {
            try { close(); } catch (Throwable cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    @Override''',1)
a=s.index('    @Override\n    public void close()');b=s.index('    private long allocate',a)
s=s[:a]+'''    @Override
    public void close() {
        if (closed) return;
        closed = true;
        if (texture != 0) GL11.glDeleteTextures(texture);
        if (glMemory != 0) EXTMemoryObject.glDeleteMemoryObjectsEXT(glMemory);
        if (view != 0) VK10.vkDestroyImageView(vk.device, view, null);
        if (image != 0) VK10.vkDestroyImage(vk.device, image, null);
        if (memory != 0) VK10.vkFreeMemory(vk.device, memory, null);
        VulkanDevice.closeHandle(exported);
        exported = -1;
    }

'''+s[b:];f.write_text(s)

f=p/'Crossing.java';s=f.read_text()
for t,n in [('long','glDone'),('long','vkDone'),('int','glDoneGl'),('int','vkDoneGl')]:
    s=s.replace(f'final {t} {n};',f'{t} {n};')
for n in ['glDoneExported','vkDoneExported']:
    s=s.replace(f'private final long {n};',f'private long {n} = -1;')
s=s.replace('    Crossing(VulkanDevice vulkanDevice) {', '    private boolean closed;\n\n    Crossing(VulkanDevice vulkanDevice) {')
s=s.replace('        this.glDone = this.semaphore();','        try {\n        this.glDone = this.semaphore();',1)
for n in ['glDone','vkDone']:
    line=f'        this.{n}Gl = Crossing.imported(this.{n}Exported);'
    s=s.replace(line,line+f'\n        this.{n}Exported = -1; // GL owns this FD now')
s=s.replace('''    }

    void handOver''','''        } catch (RuntimeException | Error failure) {
            try { close(); } catch (Throwable cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    void handOver''',1)
a=s.index('    @Override\n    public void close()');b=s.index('    private void transfer',a)
s=s[:a]+'''    @Override
    public void close() {
        if (closed) return;
        closed = true;
        if (glDoneGl != 0) EXTSemaphore.glDeleteSemaphoresEXT(glDoneGl);
        if (vkDoneGl != 0) EXTSemaphore.glDeleteSemaphoresEXT(vkDoneGl);
        if (glDone != 0) VK10.vkDestroySemaphore(vk.device, glDone, null);
        if (vkDone != 0) VK10.vkDestroySemaphore(vk.device, vkDone, null);
        VulkanDevice.closeHandle(glDoneExported); VulkanDevice.closeHandle(vkDoneExported);
        glDoneExported = vkDoneExported = -1;
    }

'''+s[b:]
a=s.index('    private static int imported(');b=s.index('    private static int[] textures',a)
s=s[:a]+'''    private static int imported(long fd) {
        VulkanDevice.glCheck("before Linux semaphore import");
        int semaphore = EXTSemaphore.glGenSemaphoresEXT();
        try {
            EXTSemaphoreFD.glImportSemaphoreFdEXT(semaphore, 38278, Math.toIntExact(fd));
            VulkanDevice.glCheck("glImportSemaphoreFdEXT");
            return semaphore;
        } catch (RuntimeException | Error failure) {
            if (semaphore != 0) EXTSemaphore.glDeleteSemaphoresEXT(semaphore);
            throw failure;
        }
    }

'''+s[b:];f.write_text(s)
