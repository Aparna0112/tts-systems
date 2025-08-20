#!/bin/bash
# Build script for TTS System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="tts-system"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-docker.io}"
DOCKER_USERNAME="${DOCKER_USERNAME:-}"
VERSION="${VERSION:-latest}"

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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Build individual service
build_service() {
    local service_name=$1
    local dockerfile_path=$2
    local image_name="${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-${service_name}:${VERSION}"
    
    print_step "Building $service_name..."
    
    if [[ ! -f "$dockerfile_path/Dockerfile" ]]; then
        print_error "Dockerfile not found at $dockerfile_path/Dockerfile"
        return 1
    fi
    
    docker build \
        --tag "$image_name" \
        --file "$dockerfile_path/Dockerfile" \
        "$dockerfile_path"
    
    print_status "$service_name built successfully: $image_name"
}

# Build all services
build_all() {
    print_status "Building all TTS System services..."
    
    # Build Gateway
    build_service "gateway" "./gateway"
    
    # Build Kokkoro
    build_service "kokkoro" "./models/kokkoro"
    
    # Build Chatterbox
    build_service "chatterbox" "./models/chatterbox"
    
    print_status "All services built successfully!"
}

# Push images to registry
push_images() {
    print_status "Pushing images to registry..."
    
    if [[ -z "$DOCKER_USERNAME" ]]; then
        print_error "DOCKER_USERNAME environment variable is required for pushing"
        exit 1
    fi
    
    # Login to Docker registry
    docker login
    
    # Push all images
    docker push "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-gateway:${VERSION}"
    docker push "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-kokkoro:${VERSION}"
    docker push "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-chatterbox:${VERSION}"
    
    print_status "Images pushed successfully!"
}

# Clean up old images
cleanup() {
    print_status "Cleaning up old images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions (keep latest)
    docker images "${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${PROJECT_NAME}-*" \
        --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}" | \
        grep -v latest | awk '{print $2}' | xargs -r docker rmi
    
    print_status "Cleanup completed!"
}

# Show help
show_help() {
    echo "TTS System Build Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build     Build all Docker images (default)"
    echo "  gateway   Build only gateway service"
    echo "  kokkoro   Build only kokkoro service"
    echo "  chatterbox Build only chatterbox service"
    echo "  push      Push images to registry"
    echo "  cleanup   Clean up old images"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_REGISTRY   Docker registry (default: docker.io)"
    echo "  DOCKER_USERNAME   Docker username (required for push)"
    echo "  VERSION          Image version tag (default: latest)"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  DOCKER_USERNAME=myuser $0 push"
    echo "  VERSION=v1.0.0 $0 build"
}

# Check prerequisites
check_prerequisites() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Main function
main() {
    local command="${1:-build}"
    
    case "$command" in
        "build")
            check_prerequisites
            build_all
            ;;
        "gateway")
            check_prerequisites
            build_service "gateway" "./gateway"
            ;;
        "kokkoro")
            check_prerequisites
            build_service "kokkoro" "./models/kokkoro"
            ;;
        "chatterbox")
            check_prerequisites
            build_service "chatterbox" "./models/chatterbox"
            ;;
        "push")
            check_prerequisites
            push_images
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
