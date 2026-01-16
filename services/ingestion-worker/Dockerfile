FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgomp1 \
    build-essential \
    cmake \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Install PyTorch CPU version from official index
RUN pip install --no-cache-dir torch==2.9.1 torchvision==0.24.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Install llama-cpp-python with limited parallelism to reduce memory usage
ENV MAX_JOBS=1
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
ENV CMAKE_ARGS="-DGGML_METAL=off"
RUN pip install --no-cache-dir llama-cpp-python==0.3.16

# Copy and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Copy models (vision model files)
COPY models/ ./models/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the worker
CMD ["python", "-m", "src.main"]
