#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - Docker Build Script
# =============================================================================
# This script provides easy Docker/Podman builds with multiple options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="rag-openshift-ai-api"
IMAGE_TAG="1.0.0"
BUILD_ENGINE="podman"
BUILD_FILE="Containerfile"
PLATFORM="linux/amd64"
PUSH_IMAGE=true
REGISTRY="quay.io/cestayg"
USE_NO_CACHE=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -n, --name NAME         Image name (default: rag-api)
    -t, --tag TAG          Image tag (default: latest)
    -e, --engine ENGINE    Build engine: podman, docker (default: podman)
    -f, --file FILE        Build file: Containerfile (default: Containerfile)
    -p, --platform PLAT    Platform: linux/amd64, linux/arm64 (default: linux/amd64)
    -r, --registry REG     Registry URL for pushing
    --push                 Push image to registry after build
    --no-cache             Build image with --no-cache
    -h, --help             Show this help message

Build Files:
    Containerfile          - Primary build file (recommended)

Build Engines:
    podman                 - Red Hat's container engine (recommended)
    docker                 - Docker engine

Examples:
    # Build with Containerfile using Podman
    $0 -f Containerfile -e podman

    # Build with Containerfile using Docker
    $0 -f Containerfile -e docker

    # Build and push to registry
    $0 -r your-registry.com -t v1.0.0 --push

    # Build for specific platform
    $0 -p linux/arm64 -f Containerfile

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if build engine is available
    if ! command -v "$BUILD_ENGINE" &> /dev/null; then
        print_error "$BUILD_ENGINE is not installed. Please install it first."
        exit 1
    fi
    
    # Check if build file exists
    if [ ! -f "$BUILD_FILE" ]; then
        print_error "Build file not found: $BUILD_FILE"
        exit 1
    fi
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found in current directory"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

# Function to build image
build_image() {
    print_info "Building image with $BUILD_ENGINE..."
    
    local full_image_name="$IMAGE_NAME:$IMAGE_TAG"
    
    # Build command
    local build_cmd="$BUILD_ENGINE build"
    
    # Add platform if specified
    if [ -n "$PLATFORM" ]; then
        build_cmd="$build_cmd --platform $PLATFORM"
    fi
    
    # Add no-cache if specified
    if [ "$USE_NO_CACHE" = true ]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    # Add build file
    build_cmd="$build_cmd -f $BUILD_FILE"
    
    # Add image name and tag
    build_cmd="$build_cmd -t $full_image_name"
    
    # Add context
    build_cmd="$build_cmd ."
    
    print_info "Command: $build_cmd"
    
    # Execute build
    if eval "$build_cmd"; then
        print_success "Image built successfully: $full_image_name"
    else
        print_error "Failed to build image"
        exit 1
    fi
}

# Function to tag for registry
tag_for_registry() {
    if [ -n "$REGISTRY" ]; then
        print_info "Tagging image for registry..."
        
        local source_image="$IMAGE_NAME:$IMAGE_TAG"
        local registry_image="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
        
        local tag_cmd="$BUILD_ENGINE tag $source_image $registry_image"
        
        print_info "Command: $tag_cmd"
        
        if eval "$tag_cmd"; then
            print_success "Image tagged for registry: $registry_image"
        else
            print_error "Failed to tag image for registry"
            exit 1
        fi
    fi
}

# Function to push image
push_image() {
    if [ "$PUSH_IMAGE" = true ] && [ -n "$REGISTRY" ]; then
        print_info "Pushing image to registry..."
        
        local registry_image="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
        
        local push_cmd="$BUILD_ENGINE push $registry_image"
        
        print_info "Command: $push_cmd"
        
        if eval "$push_cmd"; then
            print_success "Image pushed successfully: $registry_image"
        else
            print_error "Failed to push image"
            exit 1
        fi
    fi
}

# Function to show build info
show_build_info() {
    print_info "Build completed successfully!"
    echo
    print_info "Image details:"
    echo "  Name: $IMAGE_NAME"
    echo "  Tag: $IMAGE_TAG"
    echo "  Build file: $BUILD_FILE"
    echo "  Engine: $BUILD_ENGINE"
    echo "  Platform: $PLATFORM"
    
    if [ -n "$REGISTRY" ]; then
        echo "  Registry: $REGISTRY"
        echo "  Full name: $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    fi
    
    echo
    print_info "Next steps:"
    echo "  # Run locally"
    echo "  $BUILD_ENGINE run -p 8000:8000 $IMAGE_NAME:$IMAGE_TAG"
    echo
    echo "  # Deploy to OpenShift"
    echo "  oc new-build --strategy=docker --binary --name=rag-api"
    echo "  oc start-build rag-api --from-dir=. --follow"
    echo
    echo "  # Deploy with Helm"
    echo "  helm install rag-api ./helm --namespace rag-openshift-ai"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -e|--engine)
            BUILD_ENGINE="$2"
            shift 2
            ;;
        -f|--file)
            BUILD_FILE="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        --no-cache)
            USE_NO_CACHE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_info "RAG OpenShift AI API - Docker Build Script"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Build image
    build_image
    
    # Tag for registry if specified
    tag_for_registry
    
    # Push image if requested
    push_image
    
    # Show build info
    show_build_info
}

# Run main function
main "$@" 