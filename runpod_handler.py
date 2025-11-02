import runpod
import base64, tempfile, os
from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
import torch, subprocess

print("CUDA_VISIBLE_DEVICES =", os.getenv("CUDA_VISIBLE_DEVICES"))
print("torch.cuda.is_available() =", torch.cuda.is_available())
print(subprocess.getoutput("nvidia-smi"))

print("🚀 Initializing Hunyuan3D pipelines...")
shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    "tencent/Hunyuan3D-2.1"
)
paint_pipeline = Hunyuan3DPaintPipeline(
    Hunyuan3DPaintConfig(max_num_view=6, resolution=512)
)
print("✅ Pipelines ready!")


def handler(event):
    try:
        img_b64 = event.get("input_image")
        mode = event.get("mode", "full")

        if not img_b64:
            return {"error": "Missing input_image (base64 encoded)"}

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(base64.b64decode(img_b64))
        tmp.close()

        mesh_untextured = shape_pipeline(image=tmp.name)[0]

        if mode == "shape":
            mesh_untextured.export("output.obj")
            return {
                "mesh_obj": base64.b64encode(open("output.obj", "rb").read()).decode()
            }

        mesh_textured = paint_pipeline(mesh_untextured, image_path=tmp.name)
        mesh_textured.export("output.glb")
        return {"mesh_glb": base64.b64encode(open("output.glb", "rb").read()).decode()}

    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
