# Chatterbox TTS Model Dockerfile
FROM python:3.11-slim

LABEL maintainer="TTS Team"
LABEL description="Chatterbox TTS Model Service"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    MODEL_NAME=chatterbox

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libasound2-dev \
    libsndfile1-dev \
    ffmpeg \
    wget \
    curl \
    espeak-ng \
    espeak-ng-data \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for model weights and cache
RUN mkdir -p /app/weights /app/cache /app/output && \
    chmod 755 /app/weights /app/cache /app/output

# Download model weights (if needed)
# RUN python -c "from model import download_model; download_model()"

# Create non-root user
RUN groupadd -r chatterbox && useradd -r -g chatterbox chatterbox && \
    chown -R chatterbox:chatterbox /app

# Switch to non-root user
USER chatterbox

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Pre-load model on startup for faster inference
ENV PRELOAD_MODEL=true

# Command to run the application
CMD ["python", "main.py"]
