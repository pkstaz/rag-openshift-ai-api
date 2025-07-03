#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - Build Script
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="rag-openshift-ai-api"
TAG="latest"
TARGET="production"
PLATFORM="linux/amd64"
PUSH=false
VERBOSE=false
TEST_IMAGE=false
REGISTRY=""
BUILD_ARGS=""

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

# Function to cleanup on exit
cleanup() {
    if [[ -n "$TEST_CONTAINER_NAME" ]]; then
        print_info "Cleaning up test container..."
        $CONTAINER_ENGINE stop $TEST_CONTAINER_NAME > /dev/null 2>&1
        $CONTAINER_ENGINE rm $TEST_CONTAINER_NAME > /dev/null 2>&1
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [TAG]"
    echo ""
    echo "Options:"
    echo "  -n, --name IMAGE_NAME    Image name (default: rag-openshift-ai-api)"
    echo "  -t, --tag TAG           Image tag (default: latest)"
    echo "  -T, --target TARGET     Build target: production, development (default: production)"
    echo "  -p, --platform PLATFORM Target platform (default: linux/amd64)"
    echo "  -r, --registry REGISTRY Registry URL (e.g., quay.io/myorg)"
    echo "  -a, --build-arg ARG     Build argument (can be used multiple times)"
    echo "  --push                  Push image to registry after build"
    echo "  --test                  Run container test after build"
    echo "  -v, --verbose           Verbose output"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  REGISTRY               Registry URL (overrides -r option)"
    echo "  IMAGE_TAG              Tag override (overrides -t option)"
    echo "  PUSH                   Auto-push flag (overrides --push option)"
    echo "  PLATFORM               Target platform (overrides -p option)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Build production image"
    echo "  $0 v1.0.0                            # Build with specific tag"
    echo "  $0 -T development                     # Build development image"
    echo "  $0 -r quay.io/myorg --push           # Build and push to registry"
    echo "  $0 -a BUILD_DATE=\$(date) --test      # Build with args and test"
    echo "  REGISTRY=quay.io/myorg PUSH=true $0  # Using environment variables"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -T|--target)
            TARGET="$2"
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
        -a|--build-arg)
            BUILD_ARGS="$BUILD_ARGS --build-arg $2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --test)
            TEST_IMAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            # Treat as tag if it's not an option
            if [[ "$TAG" == "latest" ]]; then
                TAG="$1"
            else
                print_error "Unexpected argument: $1"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Override with environment variables if set
if [[ -n "$IMAGE_TAG" ]]; then
    TAG="$IMAGE_TAG"
fi

if [[ -n "$PLATFORM" ]]; then
    PLATFORM="$PLATFORM"
fi

if [[ "$PUSH" == "true" ]]; then
    PUSH=true
fi

if [[ -n "$REGISTRY" ]]; then
    REGISTRY="$REGISTRY"
fi

# Validate target
if [[ "$TARGET" != "production" && "$TARGET" != "development" ]]; then
    print_error "Invalid target: $TARGET. Must be 'production' or 'development'"
    exit 1
fi

# Validate tag format (basic semantic versioning check)
if [[ "$TAG" != "latest" && ! "$TAG" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$ ]]; then
    print_warning "Tag '$TAG' doesn't follow semantic versioning format (e.g., v1.0.0)"
fi

# Check if Containerfile exists
if [[ ! -f "Containerfile" ]]; then
    print_error "Containerfile not found in current directory"
    exit 1
fi

# Determine container engine (podman preferred, fallback to docker)
if command -v podman &> /dev/null; then
    CONTAINER_ENGINE="podman"
    BUILD_CMD="podman build"
    IMAGE_CMD="podman images"
    PUSH_CMD="podman push"
elif command -v docker &> /dev/null; then
    CONTAINER_ENGINE="docker"
    BUILD_CMD="docker build"
    IMAGE_CMD="docker images"
    PUSH_CMD="docker push"
else
    print_error "Neither podman nor docker found. Please install one of them."
    exit 1
fi

print_info "Using container engine: $CONTAINER_ENGINE"

# Add platform if specified
if [[ "$PLATFORM" != "" ]]; then
    BUILD_CMD="$BUILD_CMD --platform $PLATFORM"
fi

# Add target
BUILD_CMD="$BUILD_CMD --target $TARGET"

# Add build arguments if specified
if [[ -n "$BUILD_ARGS" ]]; then
    BUILD_CMD="$BUILD_CMD $BUILD_ARGS"
fi

# Construct full image name
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"
else
    FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"
fi

# Add tags
BUILD_CMD="$BUILD_CMD -t $FULL_IMAGE_NAME"

# Add additional tags if specified
if [[ "$TAG" != "latest" ]]; then
    # Add latest tag
    if [[ -n "$REGISTRY" ]]; then
        LATEST_TAG="$REGISTRY/$IMAGE_NAME:latest"
    else
        LATEST_TAG="$IMAGE_NAME:latest"
    fi
    BUILD_CMD="$BUILD_CMD -t $LATEST_TAG"
fi

# Add git commit tag if in git repository
if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
    GIT_COMMIT=$(git rev-parse --short HEAD)
    if [[ -n "$REGISTRY" ]]; then
        COMMIT_TAG="$REGISTRY/$IMAGE_NAME:$GIT_COMMIT"
    else
        COMMIT_TAG="$IMAGE_NAME:$GIT_COMMIT"
    fi
    BUILD_CMD="$BUILD_CMD -t $COMMIT_TAG"
    print_info "Git commit tag: $COMMIT_TAG"
fi

# Add context
BUILD_CMD="$BUILD_CMD ."

print_info "Building RAG OpenShift AI API container..."
print_info "Image: $FULL_IMAGE_NAME"
print_info "Target: $TARGET"
print_info "Platform: $PLATFORM"
if [[ -n "$REGISTRY" ]]; then
    print_info "Registry: $REGISTRY"
fi
if [[ "$VERBOSE" == true ]]; then
    print_info "Build command: $BUILD_CMD"
fi

# Record start time for build duration
BUILD_START=$(date +%s)

# Execute build
print_info "Starting build..."
if eval $BUILD_CMD; then
    BUILD_END=$(date +%s)
    BUILD_DURATION=$((BUILD_END - BUILD_START))
    
    print_success "Container built successfully in ${BUILD_DURATION}s!"
    
    # Show image info and size
    print_info "Image details:"
    $IMAGE_CMD $FULL_IMAGE_NAME --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # Get image size
    IMAGE_SIZE=$($IMAGE_CMD $FULL_IMAGE_NAME --format "{{.Size}}" | head -1)
    print_info "Image size: $IMAGE_SIZE"
    
    # Test image if requested
    if [[ "$TEST_IMAGE" == true ]]; then
        print_info "Testing container..."
        TEST_CONTAINER_NAME="test-rag-api-$(date +%s)"
        
        if $CONTAINER_ENGINE run --name $TEST_CONTAINER_NAME -d -p 8000:8000 $FULL_IMAGE_NAME; then
            print_info "Container started, waiting for health check..."
            sleep 5
            
            if curl -f http://localhost:8000/health > /dev/null 2>&1; then
                print_success "Container test passed!"
            else
                print_warning "Container test failed - health check unsuccessful"
            fi
            
            # Cleanup test container
            $CONTAINER_ENGINE stop $TEST_CONTAINER_NAME > /dev/null 2>&1
            $CONTAINER_ENGINE rm $TEST_CONTAINER_NAME > /dev/null 2>&1
        else
            print_warning "Container test failed - could not start container"
        fi
    fi
    
    # Push if requested
    if [[ "$PUSH" == true ]]; then
        print_info "Pushing images to registry..."
        PUSH_START=$(date +%s)
        
        # Push all tags
        PUSH_TAGS=("$FULL_IMAGE_NAME")
        
        if [[ "$TAG" != "latest" ]]; then
            PUSH_TAGS+=("$LATEST_TAG")
        fi
        
        if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
            PUSH_TAGS+=("$COMMIT_TAG")
        fi
        
        PUSH_SUCCESS=true
        for tag in "${PUSH_TAGS[@]}"; do
            print_info "Pushing tag: $tag"
            if $PUSH_CMD "$tag"; then
                print_success "Successfully pushed: $tag"
            else
                print_error "Failed to push: $tag"
                PUSH_SUCCESS=false
            fi
        done
        
        PUSH_END=$(date +%s)
        PUSH_DURATION=$((PUSH_END - PUSH_START))
        
        if [[ "$PUSH_SUCCESS" == true ]]; then
            print_success "All images pushed successfully in ${PUSH_DURATION}s!"
        else
            print_error "Some images failed to push"
            exit 1
        fi
    fi
    
    print_success "Build completed successfully!"
    print_info "To run the container:"
    echo "  $CONTAINER_ENGINE run -p 8000:8000 $FULL_IMAGE_NAME"
    
    if [[ -n "$REGISTRY" ]]; then
        print_info "Image available at: $FULL_IMAGE_NAME"
    fi
    
    # Security recommendations
    print_info "Security recommendations:"
    echo "  - Scan image for vulnerabilities: $CONTAINER_ENGINE scan $FULL_IMAGE_NAME"
    echo "  - Use specific tags in production, avoid 'latest'"
    echo "  - Regularly update base images and dependencies"
    
else
    print_error "Build failed!"
    exit 1
fi 