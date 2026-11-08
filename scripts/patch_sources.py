from pathlib import Path
import re

import sys
root = Path(sys.argv[1]).resolve()
src = root / 'src/viewpoint/upscale'

p = src / 'VulkanDevice.java'
s = p.read_text()
s = s.replace('VK_KHR_external_memory_win32', 'VK_KHR_external_memory_fd').replace('VK_KHR_external_semaphore_win32', 'VK_KHR_external_semaphore_fd')
s = s.replace('GL_EXT_memory_object_win32', 'GL_EXT_memory_object_fd').replace('GL_EXT_semaphore_win32', 'GL_EXT_semaphore_fd')
s = s.replace('import org.lwjgl.system.windows.Kernel32;', '')
s = s.replace('Configuration.VULKAN_EXPLICIT_INIT.set((Object)true);', 'Configuration.VULKAN_EXPLICIT_INIT.set(true);')
s = re.sub(r'    static void closeHandle\(long l\) \{.*?\n    \}', '''    static void closeHandle(long fd) {
        // GL takes ownership of a successfully imported OPAQUE_FD.
        // Unlike Win32 HANDLEs, it must never be closed by the caller afterwards.
    }''', s, flags=re.S)
p.write_text(s)

p = src / 'Crossing.java'
s = p.read_text().replace('EXTSemaphoreWin32', 'EXTSemaphoreFD').replace('KHRExternalSemaphoreWin32', 'KHRExternalSemaphoreFd').replace('VkSemaphoreGetWin32HandleInfoKHR', 'VkSemaphoreGetFdInfoKHR')
s = s.replace('handleTypes(2)', 'handleTypes(1)').replace('handleType(2)', 'handleType(1)')
s = s.replace('PointerBuffer pointerBuffer = memoryStack.mallocPointer(1);', 'java.nio.IntBuffer pointerBuffer = memoryStack.mallocInt(1);')
s = s.replace('vkGetSemaphoreWin32HandleKHR', 'vkGetSemaphoreFdKHR').replace('(PointerBuffer)pointerBuffer', '(java.nio.IntBuffer)pointerBuffer')
s = s.replace('glImportSemaphoreWin32HandleEXT((int)n, (int)38279, (long)l)', 'glImportSemaphoreFdEXT((int)n, (int)38278, Math.toIntExact(l))')
p.write_text(s)

p = src / 'SharedImage.java'
s = p.read_text().replace('EXTMemoryObjectWin32', 'EXTMemoryObjectFD').replace('KHRExternalMemoryWin32', 'KHRExternalMemoryFd').replace('VkMemoryGetWin32HandleInfoKHR', 'VkMemoryGetFdInfoKHR')
s = s.replace('handleTypes(2)', 'handleTypes(1)').replace('handleType(2)', 'handleType(1)')
s = s.replace('PointerBuffer pointerBuffer = memoryStack.mallocPointer(1);', 'java.nio.IntBuffer pointerBuffer = memoryStack.mallocInt(1);')
s = s.replace('vkGetMemoryWin32HandleKHR', 'vkGetMemoryFdKHR').replace('(PointerBuffer)pointerBuffer', '(java.nio.IntBuffer)pointerBuffer')
s = s.replace('glImportMemoryWin32HandleEXT((int)this.glMemory, (long)vkMemoryRequirements.size(), (int)38279, (long)this.exported)', 'glImportMemoryFdEXT((int)this.glMemory, (long)vkMemoryRequirements.size(), (int)38278, Math.toIntExact(this.exported))')
p.write_text(s)
