import runpod
import sys, os, base64, tempfile

sys.path.insert(0, "./hy3dshape")
sys.path.insert(0, "./hy3dpaint")

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig

print("🔧 Loading Hunyuan3D models...")
shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    "tencent/Hunyuan3D-2.1"
)
paint_pipeline = Hunyuan3DPaintPipeline(
    Hunyuan3DPaintConfig(max_num_view=6, resolution=512)
)
print("✅ Models ready!")


def handler(event):
    try:
        mode = os.getenv("MODEL_MODE", "full")
        img_b64 = event.get("input_image")

        if not img_b64:
            return {"error": "Missing 'input_image' (base64 encoded PNG)"}

        tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp_img.write(base64.b64decode(img_b64))
        tmp_img.close()

        mesh_untextured = shape_pipeline(image=tmp_img.name)[0]

        if mode == "shape":
            out_path = "output.obj"
            mesh_untextured.export(out_path)
            return {"mesh_obj": base64.b64encode(open(out_path, "rb").read()).decode()}

        mesh_textured = paint_pipeline(mesh_untextured, image_path=tmp_img.name)
        mesh_textured.export("output.glb")

        encoded = base64.b64encode(open("output.glb", "rb").read()).decode()
        return {"mesh_glb": encoded}
    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
