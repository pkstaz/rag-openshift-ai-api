#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - Quick Deploy Script
# =============================================================================
# Complete deployment pipeline for OpenShift

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="rag-openshift-ai"
RELEASE_NAME="rag-api"
BUILD_IMAGE=true
PUSH_IMAGE=false
REGISTRY=""
IMAGE_TAG="latest"

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
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --namespace NAMESPACE    Target namespace (default: rag-openshift-ai)"
    echo "  -r, --release RELEASE        Release name (default: rag-api)"
    echo "  --no-build                   Skip image build"
    echo "  --push                       Push image to registry"
    echo "  --registry REGISTRY          Registry URL for pushing"
    echo "  --tag TAG                    Image tag (default: latest)"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Complete deployment"
    echo "  $0 -n my-namespace --push             # Deploy with image push"
    echo "  $0 --no-build                         # Deploy without building"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if OpenShift CLI is available
    if ! command -v oc &> /dev/null; then
        print_error "OpenShift CLI (oc) is not installed. Please install it first."
        exit 1
    fi
    
    # Check if logged in to OpenShift
    if ! oc whoami &> /dev/null; then
        print_error "Not logged in to OpenShift. Please run 'oc login' first."
        exit 1
    fi
    
    # Check if namespace exists
    if ! oc get namespace $NAMESPACE &> /dev/null; then
        print_warning "Namespace $NAMESPACE does not exist. Creating it..."
        oc new-project $NAMESPACE
    fi
    
    print_success "Prerequisites check completed"
}

# Function to build and push image
build_and_push_image() {
    if [ "$BUILD_IMAGE" = true ]; then
        print_info "Building container image..."
        
        # Build image using the build script
        if [ -n "$REGISTRY" ]; then
            ./scripts/build-docker.sh \
                --registry "$REGISTRY" \
                --tag "$IMAGE_TAG" \
                --push
        else
            ./scripts/build-docker.sh \
                --tag "$IMAGE_TAG"
        fi
        
        print_success "Image build completed"
    fi
}

# Function to deploy with Helm
deploy_with_helm() {
    print_info "Deploying with Helm..."
    
    # Deploy using Helm install script
    ./scripts/helm-install.sh \
        -n "$NAMESPACE" \
        -r "$RELEASE_NAME" \
        --no-wait
    
    print_success "Helm deployment completed"
}

# Function to verify deployment
verify_deployment() {
    print_info "Verifying deployment..."
    
    # Wait for deployment to be ready
    oc rollout status deployment/"$RELEASE_NAME" -n "$NAMESPACE"
    
    # Check service
    oc get service "$RELEASE_NAME" -n "$NAMESPACE"
    
    # Check route
    oc get route "$RELEASE_NAME" -n "$NAMESPACE"
    
    print_success "Deployment verification completed"
}

# Function to show deployment info
show_deployment_info() {
    print_info "Deployment completed successfully!"
    echo
    echo "Namespace: $NAMESPACE"
    echo "Release: $RELEASE_NAME"
    echo
    echo "Next steps:"
    echo "  # Check deployment status"
    echo "  oc get all -l app.kubernetes.io/name=$RELEASE_NAME -n $NAMESPACE"
    echo
    echo "  # Get route URL"
    echo "  oc get route $RELEASE_NAME -n $NAMESPACE -o jsonpath='{.spec.host}'"
    echo
    echo "  # Check logs"
    echo "  oc logs -l app.kubernetes.io/name=$RELEASE_NAME -n $NAMESPACE -f"
    echo
    echo "  # Test API"
    echo "  curl https://$(oc get route $RELEASE_NAME -n $NAMESPACE -o jsonpath='{.spec.host}')/health"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        --no-build)
            BUILD_IMAGE=false
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
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
    print_info "RAG OpenShift AI API - Quick Deploy Script"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Build and push image
    build_and_push_image
    
    # Deploy with Helm
    deploy_with_helm
    
    # Verify deployment
    verify_deployment
    
    # Show deployment info
    show_deployment_info
}

# Run main function
main "$@" 