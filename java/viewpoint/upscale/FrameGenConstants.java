package viewpoint.upscale;
import java.util.Arrays;
import org.joml.Matrix4f;

/** Maps OpenGL clip coordinates into the SDK's zero-to-one depth/image convention. */
final class FrameGenConstants {
    static Matrix4f clipMap() { return new Matrix4f().m11(-1f).m22(0.5f).m32(0.5f); }
    static float[] pack(UpscaleFrame f, int width, int height) {
        if(f.matrices().length<64||f.camera().length<12||width<=0||height<=0)
            throw new IllegalArgumentException("invalid DLSSG camera constants");
        float[] result=new float[82];
        Matrix4f c=clipMap(), inverse=new Matrix4f(c).invert();
        Matrix4f projection=matrix(f,0),unproject=matrix(f,16);
        c.mul(projection,new Matrix4f()).get(result,0);
        unproject.mul(inverse,new Matrix4f()).get(result,16);
        c.mul(matrix(f,32),new Matrix4f()).mul(inverse).get(result,32);
        c.mul(matrix(f,48),new Matrix4f()).mul(inverse).get(result,48);
        // Column-major column-vector storage equals row-major row-vector storage.
        System.arraycopy(f.camera(),0,result,64,12);
        result[76]=f.jitterX();result[77]=f.jitterY();result[78]=f.near();result[79]=f.far();
        result[80]=f.fovY();result[81]=(float)width/height;
        for(float value:result)if(!Float.isFinite(value))throw new IllegalArgumentException("nonfinite DLSSG constants");
        return result;
    }
    private static Matrix4f matrix(UpscaleFrame f,int offset) {
        return new Matrix4f().set(Arrays.copyOfRange(f.matrices(),offset,offset+16));
    }
}
