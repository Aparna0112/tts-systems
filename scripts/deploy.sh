#!/bin/bash
# RunPod Deployment Script for TTS System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RUNPOD_API_KEY="${RUNPOD_API_KEY:-}"
PROJECT_NAME="tts-system"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-docker.io}"
DOCKER_USERNAME="${DOCKER_USERNAME:-}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed"
        exit 1
    fi
    
    if [[ -z "$RUNPOD_API_KEY" ]]; then
        print_error "RUNPOD_API_KEY environment variable is not set"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    
    # Build Gateway image
    print_status "Building Gateway image..."
    docker build -t "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-gateway:latest" ./gateway/
    
    # Build Kokkoro image
    print_status "Building Kokkoro image..."
    docker build -t "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-kokkoro:latest" ./models/kokkoro/
    
    # Build Chatterbox image
    print_status "Building Chatterbox image..."
    docker build -t "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-chatterbox:latest" ./models/chatterbox/
    
    print_status "Docker images built successfully"
}

# Push images to registry
push_images() {
    print_status "Pushing images to registry..."
    
    if [[ -n "$DOCKER_USERNAME" ]]; then
        docker login
        
        docker push "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-gateway:latest"
        docker push "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-kokkoro:latest"
        docker push "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-chatterbox:latest"
        
        print_status "Images pushed successfully"
    else
        print_warning "DOCKER_USERNAME not set, skipping image push"
    fi
}

# Deploy to RunPod
deploy_to_runpod() {
    print_status "Deploying to RunPod..."
    
    # Deploy Kokkoro model
    print_status "Deploying Kokkoro model..."
    KOKKORO_RESPONSE=$(curl -s -X POST \
        "https://api.runpod.ai/v2/endpoints" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "tts-kokkoro",
            "template": {
                "imageName": "'${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-kokkoro:latest'",
                "env": [
                    {"key": "PORT", "value": "8000"},
                    {"key": "MODEL_NAME", "value": "kokkoro"},
                    {"key": "PRELOAD_MODEL", "value": "true"}
                ],
                "containerDiskInGb": 10,
                "dockerStartCmd": "python main.py"
            },
            "locations": {
                "US-CA-1": {
                    "gpuTypeId": "NVIDIA RTX A4000",
                    "minWorkers": 0,
                    "maxWorkers": 3,
                    "scalerType": "QUEUE_DELAY",
                    "scalerSettings": {
                        "queueDelay": 5
                    }
                }
            }
        }')
    
    KOKKORO_ENDPOINT_ID=$(echo $KOKKORO_RESPONSE | jq -r '.id')
    print_status "Kokkoro endpoint created: $KOKKORO_ENDPOINT_ID"
    
    # Deploy Chatterbox model
    print_status "Deploying Chatterbox model..."
    CHATTERBOX_RESPONSE=$(curl -s -X POST \
        "https://api.runpod.ai/v2/endpoints" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "tts-chatterbox",
            "template": {
                "imageName": "'${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-chatterbox:latest'",
                "env": [
                    {"key": "PORT", "value": "8000"},
                    {"key": "MODEL_NAME", "value": "chatterbox"},
                    {"key": "PRELOAD_MODEL", "value": "true"}
                ],
                "containerDiskInGb": 10,
                "dockerStartCmd": "python main.py"
            },
            "locations": {
                "US-CA-1": {
                    "gpuTypeId": "NVIDIA RTX A4000",
                    "minWorkers": 0,
                    "maxWorkers": 3,
                    "scalerType": "QUEUE_DELAY",
                    "scalerSettings": {
                        "queueDelay": 5
                    }
                }
            }
        }')
    
    CHATTERBOX_ENDPOINT_ID=$(echo $CHATTERBOX_RESPONSE | jq -r '.id')
    print_status "Chatterbox endpoint created: $CHATTERBOX_ENDPOINT_ID"
    
    # Deploy Gateway
    print_status "Deploying Gateway..."
    GATEWAY_RESPONSE=$(curl -s -X POST \
        "https://api.runpod.ai/v2/endpoints" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "tts-gateway",
            "template": {
                "imageName": "'${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-gateway:latest'",
                "env": [
                    {"key": "PORT", "value": "8000"},
                    {"key": "KOKKORO_ENDPOINT", "value": "https://api.runpod.ai/v2/'$KOKKORO_ENDPOINT_ID'/runsync"},
                    {"key": "CHATTERBOX_ENDPOINT", "value": "https://api.runpod.ai/v2/'$CHATTERBOX_ENDPOINT_ID'/runsync"},
                    {"key": "RUNPOD_API_KEY", "value": "'$RUNPOD_API_KEY'"}
                ],
                "containerDiskInGb": 5,
                "dockerStartCmd": "python main.py"
            },
            "locations": {
                "US-CA-1": {
                    "gpuTypeId": "NVIDIA RTX A4000",
                    "minWorkers": 1,
                    "maxWorkers": 5,
                    "scalerType": "QUEUE_DELAY",
                    "scalerSettings": {
                        "queueDelay": 2
                    }
                }
            }
        }')
    
    GATEWAY_ENDPOINT_ID=$(echo $GATEWAY_RESPONSE | jq -r '.id')
    print_status "Gateway endpoint created: $GATEWAY_ENDPOINT_ID"
    
    # Save endpoint information
    cat > runpod_endpoints.txt << EOF
TTS System RunPod Deployment
===========================

Gateway Endpoint: $GATEWAY_ENDPOINT_ID
URL: https://api.runpod.ai/v2/$GATEWAY_ENDPOINT_ID/runsync

Kokkoro Endpoint: $KOKKORO_ENDPOINT_ID
URL: https://api.runpod.ai/v2/$KOKKORO_ENDPOINT_ID/runsync

Chatterbox Endpoint: $CHATTERBOX_ENDPOINT_ID
URL: https://api.runpod.ai/v2/$CHATTERBOX_ENDPOINT_ID/runsync

Environment Variables for .env:
KOKKORO_ENDPOINT=https://api.runpod.ai/v2/$KOKKORO_ENDPOINT_ID/runsync
CHATTERBOX_ENDPOINT=https://api.runpod.ai/v2/$CHATTERBOX_ENDPOINT_ID/runsync
RUNPOD_API_KEY=$RUNPOD_API_KEY
EOF
    
    print_status "Deployment information saved to runpod_endpoints.txt"
}

# Test deployment
test_deployment() {
    print_status "Testing deployment..."
    
    if [[ -f "runpod_endpoints.txt" ]]; then
        GATEWAY_ENDPOINT=$(grep "Gateway Endpoint:" runpod_endpoints.txt | cut -d' ' -f3)
        GATEWAY_URL="https://api.runpod.ai/v2/$GATEWAY_ENDPOINT/runsync"
        
        print_status "Testing gateway health..."
        HEALTH_RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
            -H "Authorization: Bearer $RUNPOD_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"input": {"path": "/health"}}' || echo "failed")
        
        if [[ "$HEALTH_RESPONSE" != "failed" ]]; then
            print_status "Gateway is responding"
        else
            print_warning "Gateway health check failed"
        fi
    else
        print_warning "No deployment information found"
    fi
}

# Main deployment process
main() {
    print_status "Starting TTS System deployment to RunPod..."
    
    check_prerequisites
    
    # Ask for confirmation
    read -p "Do you want to proceed with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
    
    build_images
    push_images
    deploy_to_runpod
    
    print_status "Waiting for endpoints to initialize..."
    sleep 30
    
    test_deployment
    
    print_status "Deployment completed successfully!"
    print_status "Check runpod_endpoints.txt for endpoint URLs and configuration"
}

# Script arguments
case "${1:-}" in
    "build")
        build_images
        ;;
    "push")
        push_images
        ;;
    "deploy")
        deploy_to_runpod
        ;;
    "test")
        test_deployment
        ;;
    *)
        main
        ;;
esac
