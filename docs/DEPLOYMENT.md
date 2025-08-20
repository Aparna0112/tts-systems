# TTS System Deployment Guide

This guide covers deploying the TTS System in various environments: local development, Docker, and RunPod.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [RunPod Deployment](#runpod-deployment)
4. [Production Considerations](#production-considerations)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd tts-system
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start services:**
   ```bash
   docker-compose up --build
   ```

4. **Verify deployment:**
   ```bash
   curl http://localhost:8000/health
   ```

### Development Mode

For active development, run services individually:

```bash
# Terminal 1 - Gateway
cd gateway
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Kokkoro Model
cd models/kokkoro
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 3 - Chatterbox Model
cd models/chatterbox
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002
```

Update `.env` for local development:
```bash
KOKKORO_ENDPOINT=http://localhost:8001
CHATTERBOX_ENDPOINT=http://localhost:8002
```

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

2. **Build and start services:**
   ```bash
   docker-compose up --build -d
   ```

3. **Check service status:**
   ```bash
   docker-compose ps
   docker-compose logs gateway
   ```

4. **Scale services if needed:**
   ```bash
   # Scale model services for higher load
   docker-compose up --scale kokkoro=2 --scale chatterbox=2 -d
   ```

### Manual Docker Build

1. **Build images:**
   ```bash
   # Build all images
   ./scripts/build.sh

   # Or build individually
   docker build -t tts-gateway ./gateway/
   docker build -t tts-kokkoro ./models/kokkoro/
   docker build -t tts-chatterbox ./models/chatterbox/
   ```

2. **Create network:**
   ```bash
   docker network create tts-network
   ```

3. **Run containers:**
   ```bash
   # Run Kokkoro
   docker run -d --name tts-kokkoro \
     --network tts-network \
     -e MODEL_NAME=kokkoro \
     -e PRELOAD_MODEL=true \
     tts-kokkoro

   # Run Chatterbox
   docker run -d --name tts-chatterbox \
     --network tts-network \
     -e MODEL_NAME=chatterbox \
     -e PRELOAD_MODEL=true \
     tts-chatterbox

   # Run Gateway
   docker run -d --name tts-gateway \
     --network tts-network \
     -p 8000:8000 \
     -e KOKKORO_ENDPOINT=http://tts-kokkoro:8001 \
     -e CHATTERBOX_ENDPOINT=http://tts-chatterbox:8002 \
     tts-gateway
   ```

### Docker Compose Configuration

**Production docker-compose.yml:**
```yaml
version: '3.8'

services:
  gateway:
    build: ./gateway
    ports:
      - "8000:8000"
    environment:
      - KOKKORO_ENDPOINT=http://kokkoro:8001
      - CHATTERBOX_ENDPOINT=http://chatterbox:8002
      - DEBUG=false
      - LOG_LEVEL=info
    depends_on:
      - kokkoro
      - chatterbox
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/quick"]
      interval: 30s
      timeout: 10s
      retries: 3

  kokkoro:
    build: ./models/kokkoro
    environment:
      - MODEL_NAME=kokkoro
      - PRELOAD_MODEL=true
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  chatterbox:
    build: ./models/chatterbox
    environment:
      - MODEL_NAME=chatterbox
      - PRELOAD_MODEL=true
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  # Optional: Add Redis for caching
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

## RunPod Deployment

### Prerequisites

1. **RunPod Account:** Sign up at [runpod.io](https://runpod.io)
2. **API Key:** Get your API key from RunPod dashboard
3. **Docker Hub Account:** For storing images

### Automated Deployment

1. **Set environment variables:**
   ```bash
   export RUNPOD_API_KEY="your-runpod-api-key"
   export DOCKER_USERNAME="your-dockerhub-username"
   ```

2. **Run deployment script:**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

3. **Check deployment info:**
   ```bash
   cat runpod_endpoints.txt
   ```

### Manual RunPod Deployment

1. **Build and push images:**
   ```bash
   # Build images
   ./scripts/build.sh

   # Push to Docker Hub
   docker login
   docker push your-username/tts-system-gateway:latest
   docker push your-username/tts-system-kokkoro:latest
   docker push your-username/tts-system-chatterbox:latest
   ```

2. **Create RunPod endpoints:**

   **Kokkoro Endpoint:**
   ```bash
   curl -X POST "https://api.runpod.ai/v2/endpoints" \
     -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "tts-kokkoro",
       "template": {
         "imageName": "your-username/tts-system-kokkoro:latest",
         "env": [
           {"key": "MODEL_NAME", "value": "kokkoro"},
           {"key": "PRELOAD_MODEL", "value": "true"}
         ],
         "containerDiskInGb": 10
       }
     }'
   ```

   **Chatterbox Endpoint:**
   ```bash
   curl -X POST "https://api.runpod.ai/v2/endpoints" \
     -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "tts-chatterbox",
       "template": {
         "imageName": "your-username/tts-system-chatterbox:latest",
         "env": [
           {"key": "MODEL_NAME", "value": "chatterbox"},
           {"key": "PRELOAD_MODEL", "value": "true"}
         ],
         "containerDiskInGb": 10
       }
     }'
   ```

   **Gateway Endpoint:**
   ```bash
   curl -X POST "https://api.runpod.ai/v2/endpoints" \
     -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "tts-gateway",
       "template": {
         "imageName": "your-username/tts-system-gateway:latest",
         "env": [
           {"key": "KOKKORO_ENDPOINT", "value": "https://api.runpod.ai/v2/kokkoro-endpoint-id/runsync"},
           {"key": "CHATTERBOX_ENDPOINT", "value": "https://api.runpod.ai/v2/chatterbox-endpoint-id/runsync"},
           {"key": "RUNPOD_API_KEY", "value": "your-api-key"}
         ]
       }
     }'
   ```

### RunPod Configuration

**Environment Variables for RunPod:**
```bash
# Gateway
KOKKORO_ENDPOINT=https://api.runpod.ai/v2/your-kokkoro-id/runsync
CHATTERBOX_ENDPOINT=https://api.runpod.ai/v2/your-chatterbox-id/runsync
RUNPOD_API_KEY=your-runpod-api-key
PORT=8000
DEBUG=false

# Models
MODEL_NAME=kokkoro  # or chatterbox
PRELOAD_MODEL=true
PORT=8000
```

## Production Considerations

### Security

1. **API Authentication:**
   ```python
   # Add to gateway main.py
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   @app.post("/tts/{model_name}")
   async def generate_tts(
       model_name: str,
       request: TTSRequest,
       token: str = Depends(security)
   ):
       # Validate token
       if not validate_api_key(token.credentials):
           raise HTTPException(401, "Invalid API key")
       # ... rest of the function
   ```

2. **Environment Variables:**
   ```bash
   # Production .env
   DEBUG=false
   API_KEY=your-secure-api-key
   ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   LOG_LEVEL=warn
   ```

3. **HTTPS Configuration:**
   ```yaml
   # docker-compose.prod.yml
   services:
     gateway:
       # ... other config
       labels:
         - "traefik.enable=true"
         - "traefik.http.routers.tts.rule=Host(`tts.yourdomain.com`)"
         - "traefik.http.routers.tts.tls=true"
         - "traefik.http.routers.tts.tls.certresolver=letsencrypt"
   ```

### Performance Optimization

1. **Resource Limits:**
   ```yaml
   # docker-compose.yml
   services:
     kokkoro:
       deploy:
         resources:
           limits:
             memory: 4G
             cpus: '2.0'
           reservations:
             memory: 2G
             cpus: '1.0'
   ```

2. **Model Preloading:**
   ```bash
   # Enable model preloading for faster response times
   PRELOAD_MODEL=true
   ```

3. **Connection Pooling:**
   ```python
   # In gateway config
   http_client = httpx.AsyncClient(
       limits=httpx.Limits(
           max_keepalive_connections=20,
           max_connections=100
       )
   )
   ```

### Scaling

1. **Horizontal Scaling:**
   ```bash
   # Scale model services
   docker-compose up --scale kokkoro=3 --scale chatterbox=2 -d
   ```

2. **Load Balancing:**
   ```yaml
   # Use Traefik or NGINX for load balancing
   services:
     traefik:
       image: traefik:v2.5
       command:
         - "--providers.docker=true"
         - "--entrypoints.web.address=:80"
       ports:
         - "80:80"
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
   ```

## Monitoring and Logging

### Health Monitoring

1. **Health Check Endpoints:**
   ```bash
   # Gateway health
   curl http://your-domain/health
   
   # Model health
   curl http://your-domain/health/models
   ```

2. **Automated Health Checks:**
   ```bash
   # Add to crontab for monitoring
   */5 * * * * curl -f http://your-domain/health/quick || echo "TTS service down" | mail admin@yourdomain.com
   ```

### Logging Configuration

1. **Structured Logging:**
   ```python
   # Add to gateway main.py
   import structlog
   
   structlog.configure(
       processors=[
           structlog.stdlib.filter_by_level,
           structlog.stdlib.add_logger_name,
           structlog.stdlib.add_log_level,
           structlog.stdlib.PositionalArgumentsFormatter(),
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.processors.JSONRenderer()
       ],
       context_class=dict,
       logger_factory=structlog.stdlib.LoggerFactory(),
       wrapper_class=structlog.stdlib.BoundLogger,
       cache_logger_on_first_use=True,
   )
   ```

2. **Log Aggregation:**
   ```yaml
   # docker-compose.yml
   services:
     gateway:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

### Metrics Collection

1. **Prometheus Integration:**
   ```python
   # Add to gateway main.py
   from prometheus_client import Counter, Histogram, make_asgi_app
   
   REQUEST_COUNT = Counter('tts_requests_total', 'Total TTS requests', ['model', 'status'])
   REQUEST_DURATION = Histogram('tts_request_duration_seconds', 'TTS request duration')
   
   # Add metrics endpoint
   metrics_app = make_asgi_app()
   app.mount("/metrics", metrics_app)
   ```

## Troubleshooting

### Common Deployment Issues

1. **Container Communication:**
   ```bash
   # Check network connectivity
   docker exec tts-gateway ping kokkoro
   docker exec tts-gateway curl http://kokkoro:8001/health
   ```

2. **Environment Variables:**
   ```bash
   # Verify environment variables
   docker exec tts-gateway env | grep ENDPOINT
   ```

3. **Resource Issues:**
   ```bash
   # Check resource usage
   docker stats
   
   # Check container logs
   docker-compose logs -f gateway
   ```

### RunPod Specific Issues

1. **Endpoint Status:**
   ```bash
   # Check RunPod endpoint status
   curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
     "https://api.runpod.ai/v2/endpoints/your-endpoint-id"
   ```

2. **Request Format:**
   ```bash
   # Test RunPod endpoint directly
   curl -X POST "https://api.runpod.ai/v2/your-endpoint-id/runsync" \
     -H "Authorization: Bearer $RUNPOD_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input": {"text": "test"}}'
   ```

### Performance Issues

1. **Model Loading:**
   ```bash
   # Check model loading time
   docker-compose logs kokkoro | grep "Model loaded"
   ```

2. **Request Timeouts:**
   ```bash
   # Increase timeout in .env
   DEFAULT_TIMEOUT=120.0
   ```

### Backup and Recovery

1. **Configuration Backup:**
   ```bash
   # Backup configuration
   tar -czf tts-config-backup.tar.gz .env docker-compose.yml
   ```

2. **Model Weights Backup:**
   ```bash
   # Backup model weights (if using persistent volumes)
   docker run --rm -v tts_kokkoro-weights:/data -v $(pwd):/backup ubuntu tar czf /backup/kokkoro-weights.tar.gz /data
   ```

This deployment guide should help you successfully deploy the TTS system in any environment. For specific issues, refer to the troubleshooting section or check the container logs for detailed error information.
