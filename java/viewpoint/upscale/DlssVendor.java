package viewpoint.upscale;
import java.util.List;
import org.lwjgl.opengl.GL11;
import org.lwjgl.vulkan.*;
/** Linux NGX Super Resolution. Frame generation and ray reconstruction are not implemented. */
final class DlssVendor implements Vendor {
    private static final int[] SCALES = {100, 67, 58, 50, 33};
    private static final int[] QUALITIES = {5, 2, 1, 0, 3};
    private final LinuxNgx ngx = new LinuxNgx();
    private boolean opened;
    static String unavailable() {
        String renderer = GL11.glGetString(GL11.GL_RENDERER);
        return renderer != null && renderer.contains("RTX") ? null : "DLSS needs an NVIDIA RTX graphics card";
    }
    public VulkanDevice.Needs needs() {
        return new VulkanDevice.Needs() {
            public List<String> instanceExtensions() { return ngx.extensions(0, 0, 0); }
            public List<String> deviceExtensions(VkInstance instance, VkPhysicalDevice physical) {
                return ngx.extensions(1, instance.address(), physical.address());
            }
        };
    }
    public Vendor.Size create(VulkanDevice vk, int scale, int width, int height) {
        int index = Vendor.nearest(SCALES, scale);
        int iw = Math.max(1, Math.round(width * SCALES[index] / 100.0f));
        int ih = Math.max(1, Math.round(height * SCALES[index] / 100.0f));
        ngx.open(vk, iw, ih, width, height, QUALITIES[index]);
        opened = true;
        System.out.println("[Viewpoint Linux DLSS] NGX initialized: " + iw + "x" + ih + " -> " + width + "x" + height);
        return new Vendor.Size(iw, ih);
    }
    public void record(VkCommandBuffer command, Vendor.Images images, UpscaleFrame frame) {
        ngx.record(command.address(), images, frame);
    }
    public void close() { if (opened) { ngx.close(); opened = false; } }
}
