# ----------------------------
# Base: Ubuntu + CUDA 12.4 + Dev Tools
# ----------------------------
    FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

    ENV DEBIAN_FRONTEND=noninteractive
    
    # --- System dependencies (build tools, OpenGL, etc.)
    RUN apt update && apt install -y \
        git wget curl python3.10 python3.10-venv python3-pip python3-dev \
        build-essential cmake ninja-build ffmpeg \
        libgl1 libglib2.0-0 libgl1-mesa-dev libglu1-mesa-dev \
        && rm -rf /var/lib/apt/lists/*
    
    WORKDIR /app
    COPY . /app
    
    # ----------------------------
    # Python Environment
    # ----------------------------
    RUN pip install --upgrade pip setuptools wheel
    
    # --- Install PyTorch (CUDA 12.4 build)
    RUN pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
        --index-url https://download.pytorch.org/whl/cu124
    
    # ----------------------------
    # Install dependencies
    # ----------------------------
    
    # Blender Python API (bpy) comes from Blender's own index
    RUN pip install --extra-index-url https://download.blender.org/pypi/ bpy==4.0
    
    # Optional environment flags to skip heavy CUDA ops in some libs
    ENV FORCE_CUDA=0
    ENV MMCV_WITH_OPS=0
    
    # Main Python requirements
    RUN pip install --prefer-binary -r requirements.txt
    
    # ----------------------------
    # Compile custom modules
    # ----------------------------
    
    # Avoid build isolation (torch visibility) + disable git version lookup
    ENV PIP_NO_BUILD_ISOLATION=1
    ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
    
    # Compile Custom Rasterizer
    RUN cd hy3dpaint/custom_rasterizer && pip install -e . && cd ../..
    
    # Compile Differentiable Renderer (Docker-safe)
    RUN cd hy3dpaint/DifferentiableRenderer && bash compile_mesh_painter.sh && cd ../..
    
    # ----------------------------
    # Download ESRGAN checkpoint
    # ----------------------------
    RUN mkdir -p hy3dpaint/ckpt && \
        wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth \
        -P hy3dpaint/ckpt
    
    # ----------------------------
    # Install API runtime deps
    # ----------------------------
    RUN pip install fastapi uvicorn runpod
    
    # ----------------------------
    # Entrypoint
    # ----------------------------
    COPY runpod_handler.py /app/runpod_handler.py
    ENV PYTHONUNBUFFERED=1
    
    CMD ["python3", "runpod_handler.py"]
    