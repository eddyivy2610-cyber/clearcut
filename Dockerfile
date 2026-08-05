FROM python:3.11.9-slim

# Install system dependencies required for OpenCV and curl
RUN apt-get update && apt-get install -y \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the u2netp ONNX model into /root/.u2net to avoid runtime network download failures
RUN mkdir -p /root/.u2net && \
    curl -L -o /root/.u2net/u2netp.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx

COPY app.py app.py
COPY templates templates
COPY static static

EXPOSE 5000

ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1

CMD gunicorn --workers 1 --threads 2 --timeout 120 -b 0.0.0.0:$PORT app:app