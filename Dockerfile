FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y \
    git wget python3.10 python3.10-venv python3-pip build-essential cmake ninja-build libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip setuptools wheel
RUN pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

# prevent optional CUDA ops from hanging
ENV FORCE_CUDA=0
ENV MMCV_WITH_OPS=0

RUN pip install -r requirements.txt

# --- Compile rasterizer and differentiable renderer
RUN cd hy3dpaint/custom_rasterizer && pip install -e . && cd ../..
RUN cd hy3dpaint/DifferentiableRenderer && bash compile_mesh_painter.sh && cd ../..

# --- Download ESRGAN weights
RUN mkdir -p hy3dpaint/ckpt && \
    wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -P hy3dpaint/ckpt

# --- API server
RUN pip install fastapi uvicorn
COPY runpod_handler.py /app/runpod_handler.py

ENV PYTHONUNBUFFERED=1
CMD ["python3", "runpod_handler.py"]
