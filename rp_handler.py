"""
RunPod Serverless Handler for Hunyuan3D-2.1

This handler integrates the Hunyuan3D model with RunPod's serverless platform.
It processes incoming requests to generate 3D models from images.
"""
import runpod
import os
import sys
import uuid
import base64
import time
import traceback
from io import BytesIO
from PIL import Image
import torch

# Add paths for imports
sys.path.insert(0, './hy3dshape')
sys.path.insert(0, './hy3dpaint')

# Apply torchvision compatibility fix before other imports
try:
    from torchvision_fix import apply_fix
    apply_fix()
except ImportError:
    print("Warning: torchvision_fix module not found, proceeding without compatibility fix")
except Exception as e:
    print(f"Warning: Failed to apply torchvision fix: {e}")

from hy3dshape import Hunyuan3DDiTFlowMatchingPipeline
from hy3dshape.rembg import BackgroundRemover
from hy3dshape.utils import logger
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
from hy3dpaint.convert_utils import create_glb_with_pbr_materials

# Configuration
SAVE_DIR = os.environ.get('SAVE_DIR', '/runpod-volume/outputs')
MODEL_PATH = os.environ.get('MODEL_PATH', 'tencent/Hunyuan3D-2.1')
SUBFOLDER = os.environ.get('SUBFOLDER', 'hunyuan3d-dit-v2-1')
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# Create output directory
os.makedirs(SAVE_DIR, exist_ok=True)

print(f"Initializing Hunyuan3D-2.1 on {DEVICE}...")
print(f"Model path: {MODEL_PATH}")
print(f"Save directory: {SAVE_DIR}")


def quick_convert_with_obj2gltf(obj_path: str, glb_path: str):
    """Convert OBJ with PBR textures to GLB format"""
    textures = {
        'albedo': obj_path.replace('.obj', '.jpg'),
        'metallic': obj_path.replace('.obj', '_metallic.jpg'),
        'roughness': obj_path.replace('.obj', '_roughness.jpg')
    }
    create_glb_with_pbr_materials(obj_path, textures, glb_path)


def load_image_from_base64(image_str):
    """Load an image from base64 encoded string"""
    # Remove data URL prefix if present
    if 'base64,' in image_str:
        image_str = image_str.split('base64,')[1]
    return Image.open(BytesIO(base64.b64decode(image_str)))


# Initialize models globally (outside handler for efficiency)
print("Loading background remover...")
rembg = BackgroundRemover()

print("Loading shape generation pipeline...")
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(MODEL_PATH)

# Enable optimizations if available
enable_flashvdm = os.environ.get('ENABLE_FLASHVDM', 'false').lower() == 'true'
compile_model = os.environ.get('COMPILE_MODEL', 'false').lower() == 'true'

if enable_flashvdm:
    mc_algo = 'mc' if DEVICE in ['cpu', 'mps'] else os.environ.get('MC_ALGO', 'mc')
    print(f"Enabling FlashVDM with mc_algo={mc_algo}...")
    pipeline.enable_flashvdm(mc_algo=mc_algo)

if compile_model:
    print("Compiling model...")
    pipeline.compile()

print("Loading texture generation pipeline...")
max_num_view = 6
resolution = 512
conf = Hunyuan3DPaintConfig(max_num_view, resolution)
conf.realesrgan_ckpt_path = "hy3dpaint/ckpt/RealESRGAN_x4plus.pth"
conf.multiview_cfg_path = "hy3dpaint/cfgs/hunyuan-paint-pbr.yaml"
conf.custom_pipeline = "hy3dpaint/hunyuanpaintpbr"
paint_pipeline = Hunyuan3DPaintPipeline(conf)

print("Model initialization complete!")


def handler(job):
    """
    RunPod handler function for 3D model generation.
    
    Expected input format:
    {
        "input": {
            "image": "base64_encoded_image_string",
            "texture": true,  // Optional, default: true
            "remove_background": true,  // Optional, default: true
            "seed": 1234  // Optional, default: 1234
        }
    }
    
    Returns:
    {
        "model_base64": "base64_encoded_glb_file",
        "generation_time": 12.34
    }
    """
    try:
        job_input = job["input"]
        job_id = job.get("id", str(uuid.uuid4()))
        
        print(f"Processing job: {job_id}")
        start_time = time.time()
        
        # Extract parameters
        image_b64 = job_input.get("image")
        if not image_b64:
            return {"error": "Missing required parameter: 'image'"}
        
        generate_texture = job_input.get("texture", True)
        remove_bg = job_input.get("remove_background", True)
        seed = job_input.get("seed", 1234)
        
        # Set random seed for reproducibility
        if seed:
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
        
        # Update progress
        runpod.serverless.progress_update(job, "Loading image...")
        
        # Load and preprocess image
        print(f"Loading image (remove_background={remove_bg})...")
        image = load_image_from_base64(image_b64)
        image = image.convert("RGBA")
        
        if remove_bg and image.mode == "RGB":
            print("Removing background...")
            image = rembg(image)
        
        # Generate mesh
        runpod.serverless.progress_update(job, "Generating 3D mesh...")
        print("Generating 3D mesh...")
        
        with torch.inference_mode():
            mesh = pipeline(image=image)[0]
        
        mesh_time = time.time() - start_time
        print(f"Mesh generation completed in {mesh_time:.2f} seconds")
        
        # Save initial mesh
        uid = str(uuid.uuid4())
        initial_save_path = os.path.join(SAVE_DIR, f'{uid}_initial.glb')
        mesh.export(initial_save_path)
        
        # Generate textures if requested
        if generate_texture:
            runpod.serverless.progress_update(job, "Generating textures...")
            print("Generating textures...")
            
            try:
                output_mesh_path_obj = os.path.join(SAVE_DIR, f'{uid}_texturing.obj')
                textured_path_obj = paint_pipeline(
                    mesh_path=initial_save_path,
                    image_path=image,
                    output_mesh_path=output_mesh_path_obj,
                    save_glb=False
                )
                
                # Convert textured OBJ to GLB
                print("Converting textured OBJ to GLB...")
                glb_path_textured = os.path.join(SAVE_DIR, f'{uid}_texturing.glb')
                quick_convert_with_obj2gltf(textured_path_obj, glb_path_textured)
                
                final_save_path = os.path.join(SAVE_DIR, f'{uid}_textured.glb')
                os.rename(glb_path_textured, final_save_path)
                
                print(f"Texture generation completed")
                
            except Exception as e:
                print(f"Texture generation failed: {e}")
                print("Using untextured mesh as fallback")
                final_save_path = initial_save_path
        else:
            final_save_path = initial_save_path
        
        # Read and encode the final model
        runpod.serverless.progress_update(job, "Encoding output...")
        print("Encoding output...")
        
        with open(final_save_path, 'rb') as f:
            model_bytes = f.read()
            model_base64 = base64.b64encode(model_bytes).decode('utf-8')
        
        # Clean up temporary files
        try:
            if os.path.exists(initial_save_path):
                os.remove(initial_save_path)
            if generate_texture:
                for ext in ['.obj', '.jpg', '_metallic.jpg', '_roughness.jpg', '.mtl']:
                    temp_file = os.path.join(SAVE_DIR, f'{uid}_texturing{ext}')
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            if os.path.exists(final_save_path):
                os.remove(final_save_path)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary files: {e}")
        
        total_time = time.time() - start_time
        print(f"Job {job_id} completed in {total_time:.2f} seconds")
        
        # Return results
        return {
            "model_base64": model_base64,
            "generation_time": round(total_time, 2),
            "textured": generate_texture,
            "job_id": job_id
        }
        
    except Exception as e:
        print(f"Error processing job: {e}")
        traceback.print_exc()
        return {"error": str(e), "traceback": traceback.format_exc()}


# Start the RunPod serverless function
if __name__ == "__main__":
    print("Starting RunPod serverless worker...")
    runpod.serverless.start({"handler": handler})
