# RunPod Serverless Deployment Guide
## Hunyuan3D-2.1 Model

This guide explains how to deploy the Hunyuan3D-2.1 model on RunPod's serverless platform using Git integration.

## Overview

The deployment includes:
- **Handler**: `rp_handler.py` - RunPod serverless handler
- **Dockerfile**: `Dockerfile.runpod` - Container configuration
- **Test Input**: `test_input.json` - Sample request for local testing

## Prerequisites

1. ✅ RunPod account ([create one](https://runpod.io))
2. ✅ Git repository with RunPod integration configured
3. ✅ Docker Hub account (for custom image builds)
4. ✅ NVIDIA GPU support (CUDA 12.1+)

## Architecture

The handler follows RunPod's serverless architecture:

```
Client Request → RunPod Endpoint → Worker (rp_handler.py)
                                      ↓
                                  Process Job
                                      ↓
                              Return Base64 GLB
```

### Handler Features

- **Automatic model initialization** - Models loaded once at startup
- **Progress updates** - Real-time job status updates
- **Error handling** - Comprehensive error reporting
- **Texture generation** - Optional PBR texture support
- **Background removal** - Automatic background removal
- **Base64 output** - Direct base64-encoded GLB output

## Local Testing

Before deploying to RunPod, test the handler locally:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install runpod
```

### 2. Run Handler Locally

Using the provided test input:
```bash
python rp_handler.py
```

Or with custom input:
```bash
python rp_handler.py --test_input '{"input": {"image": "YOUR_BASE64_IMAGE", "texture": true}}'
```

### 3. Expected Output

```
--- Starting Serverless Worker |  Version 1.x.x ---
INFO   | Using test_input.json as job input.
INFO   | local_test | Started.
Processing job: local_test
Loading image...
Generating 3D mesh...
Mesh generation completed in X.XX seconds
Generating textures...
INFO   | Job local_test completed successfully.
```

## Deployment Methods

### Method 1: RunPod Git Integration (Recommended)

Since you've already configured Git integration, use this method:

#### Step 1: Push to Repository

Ensure all files are committed and pushed:
```bash
git add rp_handler.py Dockerfile.runpod test_input.json .dockerignore
git commit -m "Add RunPod serverless configuration"
git push origin main
```

#### Step 2: Create RunPod Endpoint

1. Go to [RunPod Serverless Console](https://www.runpod.io/console/serverless)
2. Click **New Endpoint**
3. Select **Import from Git Repository**
4. Configure:
   - **Repository**: Select your configured Git repo
   - **Branch**: `main` (or your deployment branch)
   - **Dockerfile Path**: `Dockerfile.runpod`
   - **Handler**: `rp_handler.py`
5. Click **Next**

#### Step 3: Configure Endpoint Settings

**Basic Settings:**
- **Name**: `hunyuan3d-2-1` (or custom name)
- **Endpoint Type**: `Queue` (for job queuing)
- **GPU Configuration**: 
  - ✅ **24 GB VRAM** (Recommended: RTX 4090, RTX A5000)
  - Or **16 GB VRAM** (Minimum: RTX 4000)

**Advanced Settings:**
- **Max Workers**: `3` (adjust based on demand)
- **Idle Timeout**: `60 seconds`
- **Container Disk**: `20 GB`
- **Volume Mount**: `/runpod-volume` (for persistent storage)

**Environment Variables** (Optional):
```
SAVE_DIR=/runpod-volume/outputs
MODEL_PATH=tencent/Hunyuan3D-2.1
ENABLE_FLASHVDM=false
COMPILE_MODEL=false
```

#### Step 4: Deploy

1. Click **Deploy Endpoint**
2. Wait for workers to initialize (2-5 minutes)
3. Endpoint will be ready when status shows "Active"

### Method 2: Docker Hub Deployment

If you prefer building and pushing a custom Docker image:

#### Step 1: Build Image

```bash
docker build -f Dockerfile.runpod -t your-dockerhub-username/hunyuan3d-runpod:latest .
```

#### Step 2: Push to Docker Hub

```bash
docker login
docker push your-dockerhub-username/hunyuan3d-runpod:latest
```

#### Step 3: Create RunPod Endpoint

1. Go to [RunPod Serverless Console](https://www.runpod.io/console/serverless)
2. Click **New Endpoint**
3. Select **Import from Docker Registry**
4. Enter: `docker.io/your-dockerhub-username/hunyuan3d-runpod:latest`
5. Configure settings as in Method 1, Step 3
6. Click **Deploy**

## Using the Endpoint

### Python SDK

```python
import runpod
import base64

# Initialize client
runpod.api_key = "YOUR_RUNPOD_API_KEY"
endpoint = runpod.Endpoint("YOUR_ENDPOINT_ID")

# Load and encode image
with open("input_image.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode('utf-8')

# Run job
job = endpoint.run({
    "image": image_b64,
    "texture": True,
    "remove_background": True,
    "seed": 1234
})

# Wait for completion
result = job.output()

# Save generated model
if "model_base64" in result:
    model_data = base64.b64decode(result["model_base64"])
    with open("output_model.glb", "wb") as f:
        f.write(model_data)
    print(f"Model saved! Generation time: {result['generation_time']}s")
```

### cURL

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -d '{
    "input": {
      "image": "BASE64_ENCODED_IMAGE",
      "texture": true,
      "remove_background": true,
      "seed": 1234
    }
  }'
```

### JavaScript/Node.js

```javascript
const runpod = require('runpod-sdk');

const client = new runpod.Client('YOUR_RUNPOD_API_KEY');
const endpoint = client.endpoint('YOUR_ENDPOINT_ID');

// Load and encode image
const fs = require('fs');
const imageBuffer = fs.readFileSync('input_image.png');
const imageBase64 = imageBuffer.toString('base64');

// Run job
const job = await endpoint.run({
  input: {
    image: imageBase64,
    texture: true,
    remove_background: true,
    seed: 1234
  }
});

// Wait for result
const result = await job.output();

// Save model
if (result.model_base64) {
  const modelBuffer = Buffer.from(result.model_base64, 'base64');
  fs.writeFileSync('output_model.glb', modelBuffer);
  console.log(`Model saved! Generation time: ${result.generation_time}s`);
}
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | string | ✅ Yes | - | Base64-encoded input image (PNG, JPG, JPEG) |
| `texture` | boolean | No | `true` | Generate PBR textures (albedo, metallic, roughness) |
| `remove_background` | boolean | No | `true` | Automatically remove image background |
| `seed` | integer | No | `1234` | Random seed for reproducible results |

## Output Format

```json
{
  "model_base64": "BASE64_ENCODED_GLB_FILE",
  "generation_time": 12.34,
  "textured": true,
  "job_id": "unique-job-id"
}
```

Or on error:
```json
{
  "error": "Error message",
  "traceback": "Full error traceback"
}
```

## Monitoring

### Check Endpoint Health

```python
import requests

response = requests.get(
    f"https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/health",
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)
print(response.json())
```

### View Logs

1. Go to RunPod Console
2. Select your endpoint
3. Click on **Logs** tab
4. View real-time worker logs

### Check Job Status

```python
# Check specific job
job_status = endpoint.status("JOB_ID")
print(job_status)
```

## Performance Optimization

### 1. Model Caching

Pre-download models into the Docker image (increases image size):

Uncomment in `Dockerfile.runpod`:
```dockerfile
RUN python3 -c "from hy3dshape import Hunyuan3DDiTFlowMatchingPipeline; \
    Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2.1')"
```

### 2. Enable FlashVDM

For faster inference, set environment variable:
```
ENABLE_FLASHVDM=true
MC_ALGO=mc_fast
```

### 3. Model Compilation

Enable PyTorch compilation (increases startup time):
```
COMPILE_MODEL=true
```

### 4. Adjust Worker Count

Scale based on demand:
- **Low traffic**: 1-2 workers
- **Medium traffic**: 3-5 workers
- **High traffic**: 5-10 workers

## Cost Estimation

Approximate costs per generation (prices vary):

| GPU Type | VRAM | Cost per Hour | Est. per Generation* |
|----------|------|---------------|---------------------|
| RTX 4000 | 16 GB | $0.34 | $0.01 - $0.02 |
| RTX 4090 | 24 GB | $0.69 | $0.02 - $0.03 |
| RTX A5000 | 24 GB | $0.89 | $0.02 - $0.04 |

\* Based on ~5-15 seconds per generation with textures

## Troubleshooting

### Issue: Workers Not Starting

**Solution:**
- Check Docker image build logs
- Verify CUDA compatibility (requires CUDA 12.1+)
- Ensure sufficient container disk space (20 GB+)

### Issue: Out of Memory Errors

**Solution:**
- Use 24 GB GPU configuration
- Reduce `max_num_view` in handler
- Disable texture generation for testing

### Issue: Slow Model Loading

**Solution:**
- Pre-download models into Docker image
- Use RunPod's network storage for model cache
- Enable persistent volumes

### Issue: Job Timeouts

**Solution:**
- Increase endpoint timeout settings
- Check GPU availability
- Monitor worker logs for bottlenecks

## Best Practices

1. **Use Network Storage**: Store model weights on RunPod's network storage for faster cold starts
2. **Implement Retries**: Add retry logic for transient failures
3. **Monitor Costs**: Set up billing alerts in RunPod dashboard
4. **Version Control**: Tag Docker images with version numbers
5. **Test Locally**: Always test with `test_input.json` before deploying
6. **Health Checks**: Implement custom health check endpoints
7. **Error Handling**: Log errors comprehensively for debugging

## Scaling Strategies

### Auto-scaling Configuration

Configure in RunPod dashboard:
- **Min Workers**: `1` (always-on for low latency)
- **Max Workers**: `10` (scale up during peak)
- **Scale Up Threshold**: `5 jobs in queue`
- **Scale Down Threshold**: `0 jobs for 60 seconds`

### Load Balancing

RunPod automatically load-balances across workers. For custom routing:
- Use multiple endpoints for different model configurations
- Route texture/non-texture requests separately
- Implement client-side load balancing

## Security Considerations

1. **API Keys**: Never commit API keys to repository
2. **Input Validation**: Handler validates all inputs
3. **Rate Limiting**: Configure in RunPod dashboard
4. **Image Size Limits**: Enforce max image size (e.g., 10 MB)
5. **Model Access**: Use private Docker registries for proprietary models

## Support and Resources

- **RunPod Documentation**: https://docs.runpod.io
- **RunPod Discord**: https://discord.gg/runpod
- **Hunyuan3D Repository**: https://github.com/Tencent/Hunyuan3D-2
- **Issue Tracking**: Create issues in your repository

## Updates and Maintenance

### Update Deployment

1. Make changes to `rp_handler.py` or `Dockerfile.runpod`
2. Commit and push to Git
3. In RunPod console, click **Redeploy** on your endpoint
4. RunPod will rebuild and deploy the updated image

### Model Updates

To update to a newer model version:
1. Change `MODEL_PATH` environment variable
2. Rebuild Docker image or redeploy from Git
3. Test with sample inputs before production deployment

## Conclusion

Your Hunyuan3D-2.1 model is now configured for RunPod serverless deployment. The handler provides:

✅ Automatic model initialization  
✅ Progress tracking  
✅ Error handling  
✅ Texture generation  
✅ Base64 output  
✅ Cost-effective scaling  

For questions or issues, refer to the troubleshooting section or contact RunPod support.

---

**Last Updated**: 2025-11-02  
**RunPod API Version**: v2  
**Handler Version**: 1.0.0
