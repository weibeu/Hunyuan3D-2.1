"""
Test script for RunPod Serverless Endpoint
Hunyuan3D-2.1 Model

Usage:
    python test_runpod_endpoint.py --api-key YOUR_API_KEY --endpoint-id YOUR_ENDPOINT_ID --image path/to/image.png
"""
import argparse
import base64
import time
import sys
from pathlib import Path

try:
    import runpod
except ImportError:
    print("Error: runpod package not installed. Install with: pip install runpod")
    sys.exit(1)


def load_image_as_base64(image_path):
    """Load an image file and convert to base64"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')


def test_endpoint(api_key, endpoint_id, image_path, texture=True, remove_background=True, seed=1234):
    """Test the RunPod endpoint with an image"""
    
    print(f"Testing RunPod Endpoint: {endpoint_id}")
    print(f"Image: {image_path}")
    print(f"Texture: {texture}, Remove BG: {remove_background}, Seed: {seed}")
    print("-" * 60)
    
    # Initialize RunPod client
    runpod.api_key = api_key
    endpoint = runpod.Endpoint(endpoint_id)
    
    # Load image
    print("\n[1/4] Loading image...")
    try:
        image_b64 = load_image_as_base64(image_path)
        print(f"✓ Image loaded ({len(image_b64)} bytes base64)")
    except Exception as e:
        print(f"✗ Failed to load image: {e}")
        return False
    
    # Submit job
    print("\n[2/4] Submitting job to endpoint...")
    try:
        job = endpoint.run({
            "image": image_b64,
            "texture": texture,
            "remove_background": remove_background,
            "seed": seed
        })
        job_id = job.job_id
        print(f"✓ Job submitted: {job_id}")
    except Exception as e:
        print(f"✗ Failed to submit job: {e}")
        return False
    
    # Wait for completion with progress updates
    print("\n[3/4] Waiting for job completion...")
    start_time = time.time()
    last_status = None
    
    while True:
        try:
            status = job.status()
            current_status = status.get('status')
            
            if current_status != last_status:
                print(f"  Status: {current_status}")
                last_status = current_status
            
            if current_status == 'COMPLETED':
                break
            elif current_status == 'FAILED':
                print(f"✗ Job failed: {status.get('error', 'Unknown error')}")
                return False
            
            time.sleep(2)
            
        except Exception as e:
            print(f"✗ Error checking status: {e}")
            return False
    
    wait_time = time.time() - start_time
    print(f"✓ Job completed in {wait_time:.2f} seconds")
    
    # Get results
    print("\n[4/4] Retrieving results...")
    try:
        result = job.output()
        
        if "error" in result:
            print(f"✗ Job returned error: {result['error']}")
            if "traceback" in result:
                print(f"\nTraceback:\n{result['traceback']}")
            return False
        
        # Save model file
        if "model_base64" in result:
            model_data = base64.b64decode(result["model_base64"])
            
            # Generate output filename
            input_name = Path(image_path).stem
            output_name = f"output_{input_name}_{int(time.time())}.glb"
            
            with open(output_name, 'wb') as f:
                f.write(model_data)
            
            print(f"✓ Model saved: {output_name}")
            print(f"  Size: {len(model_data) / 1024:.2f} KB")
            print(f"  Generation time: {result.get('generation_time', 'N/A')}s")
            print(f"  Textured: {result.get('textured', 'N/A')}")
            print(f"  Job ID: {result.get('job_id', job_id)}")
            
            print("\n" + "="*60)
            print("SUCCESS! 3D model generated successfully!")
            print("="*60)
            return True
        else:
            print("✗ No model data in response")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to get results: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test RunPod Serverless Endpoint for Hunyuan3D-2.1"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        required=True,
        help="RunPod API key"
    )
    parser.add_argument(
        "--endpoint-id",
        type=str,
        required=True,
        help="RunPod endpoint ID"
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to input image"
    )
    parser.add_argument(
        "--texture",
        action="store_true",
        default=True,
        help="Generate textures (default: True)"
    )
    parser.add_argument(
        "--no-texture",
        action="store_true",
        help="Disable texture generation"
    )
    parser.add_argument(
        "--no-remove-bg",
        action="store_true",
        help="Disable background removal"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1234,
        help="Random seed (default: 1234)"
    )
    
    args = parser.parse_args()
    
    # Validate image path
    if not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)
    
    # Run test
    texture = not args.no_texture
    remove_bg = not args.no_remove_bg
    
    success = test_endpoint(
        api_key=args.api_key,
        endpoint_id=args.endpoint_id,
        image_path=args.image,
        texture=texture,
        remove_background=remove_bg,
        seed=args.seed
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
