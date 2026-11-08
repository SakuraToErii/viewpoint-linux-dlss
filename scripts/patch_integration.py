"""Apply integration changes to a locally decompiled, hash-pinned upstream JAR."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
source=root/'src/viewpoint/upscale/Upscaling.java'
text=source.read_text()
start=text.index('    private Upscaling(')
end=text.index('    public static Upscaling open',start)
replacement="    private Upscaling(Kind kind, int n, int n2, int n3) {\n        this.kind = kind;\n        this.scale = n;\n        this.outputWidth = n2;\n        this.outputHeight = n3;\n        Vendor newVendor = null;\n        VulkanDevice newVk = null;\n        Crossing newCrossing = null;\n        SharedImage[] created = new SharedImage[4];\n        try {\n            newVendor = kind.vendor.get();\n            newVk = VulkanDevice.open(newVendor.needs());\n            newCrossing = new Crossing(newVk);\n            Vendor.Size size = newVendor.create(newVk, n, n2, n3);\n            created[0] = new SharedImage(newVk, 97, 34842, size.width(), size.height());\n            created[1] = new SharedImage(newVk, 100, 33326, size.width(), size.height());\n            created[2] = new SharedImage(newVk, 83, 33327, size.width(), size.height());\n            created[3] = new SharedImage(newVk, 97, 34842, n2, n3);\n            GL11.glFinish();\n            this.vendor = newVendor;\n            this.vk = newVk;\n            this.crossing = newCrossing;\n            this.frameWidth = size.width();\n            this.frameHeight = size.height();\n            this.images = new Vendor.Images(created[0], created[1], created[2], created[3]);\n            this.all = created;\n        } catch (RuntimeException | Error failure) {\n            if (newVk != null) try { newVk.idle(); } catch (Throwable cleanup) { failure.addSuppressed(cleanup); }\n            cleanup(newVendor, failure);\n            cleanup(newCrossing, failure);\n            for (SharedImage image : created) cleanup(image, failure);\n            cleanup(newVk, failure);\n            throw failure;\n        }\n    }\n\n    private static void cleanup(AutoCloseable resource, Throwable failure) {\n        if (resource != null) try { resource.close(); } catch (Throwable cleanup) { failure.addSuppressed(cleanup); }\n    }\n\n"
text=text[:start]+replacement+text[end:]
marker='        public String unsupported() {\n'
assert text.count(marker)==1
text=text.replace(marker,marker+'            if (this != DLSS) return "this local Linux port currently supports DLSS Super Resolution only";\n',1)
source.write_text(text)
