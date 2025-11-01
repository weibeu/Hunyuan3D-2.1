# Hunyuan3D 2.1 — RunPod Serverless

## 🚀 Steps to Deploy

1. Fork this repo.
2. Add your RunPod `Dockerfile`, `runpod_handler.py`, and `app_config.json`.
3. Push to GitHub.
4. In RunPod Dashboard → **Serverless → Create Template**:
    - Paste the `app_config.json` contents.
    - Select GPU (A100 / A40).
    - Set **Container Disk**: 100GB.
    - Choose **CUDA 12.4**.

## 🧪 Test Input

Use `serverless/sample_input.json` as request payload.

Returns base64 encoded `.obj` or `.glb` file.
