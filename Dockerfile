# ------------------------------------------
# Base: Official Tencent prebuilt image
# ------------------------------------------
FROM registry.hf.space/tencent-hunyuan3d-2-1:latest

LABEL name="hunyuan3d21-runpod" maintainer="you@example.com"

# Switch working directory to repo
WORKDIR /workspace/Hunyuan3D-2.1

# Install RunPod & FastAPI inside the same Conda env
RUN /workspace/miniconda3/bin/conda run -n hunyuan3d21 pip install --no-cache-dir fastapi uvicorn runpod

# Add your RunPod handler
COPY runpod_handler.py /workspace/Hunyuan3D-2.1/runpod_handler.py

# --- CUDA + runtime environment ---
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="/workspace/miniconda3/envs/hunyuan3d21/bin:${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="/workspace/miniconda3/envs/hunyuan3d21/lib:${CUDA_HOME}/lib64:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"
ENV TORCH_CUDA_ARCH_LIST="6.0;6.1;7.0;7.5;8.0;8.6;8.9;9.0"

# --- Other runtime flags ---
ENV PYTHONUNBUFFERED=1
ENV PYOPENGL_PLATFORM=egl

# No ports needed; this is serverless
CMD ["/workspace/miniconda3/bin/conda", "run", "-n", "hunyuan3d21", "python", "runpod_handler.py"]
