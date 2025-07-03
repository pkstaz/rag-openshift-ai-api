#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - OpenShift Build Script
# =============================================================================
# This script handles OpenShift builds correctly with proper command separation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BUILD_NAME="rag-api"
BUILD_FILE="Containerfile"
NAMESPACE="rag-openshift-ai"
FOLLOW_BUILD=true
DRY_RUN=false

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
    -n, --name NAME         Build name (default: rag-api)
    -f, --file FILE        Build file: Containerfile, Dockerfile (default: Containerfile)
    -p, --namespace NS     Namespace (default: rag-openshift-ai)
    --no-follow            Don't follow build logs
    -d, --dry-run          Show commands without executing
    -h, --help             Show this help message

Build Files:
    Containerfile          - Primary build file (recommended)
    Dockerfile             - Compatibility build file

Examples:
    # Build with Containerfile (recommended)
    $0 -f Containerfile

    # Build with Dockerfile
    $0 -f Dockerfile

    # Build in different namespace
    $0 -p my-namespace -f Containerfile

    # Dry run to see commands
    $0 -d -f Containerfile

EOF
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
    
    # Check if build file exists
    if [ ! -f "$BUILD_FILE" ]; then
        print_error "Build file not found: $BUILD_FILE"
        exit 1
    fi
    
    # Check if namespace exists
    if ! oc get project "$NAMESPACE" &> /dev/null; then
        print_warning "Namespace $NAMESPACE does not exist. Creating it..."
        if [ "$DRY_RUN" = false ]; then
            oc new-project "$NAMESPACE"
        fi
    fi
    
    print_success "Prerequisites check completed"
}

# Function to create build configuration
create_build_config() {
    print_info "Creating build configuration..."
    
    local build_cmd="oc new-build --strategy=docker --binary --name=$BUILD_NAME"
    
    # Add dockerfile if specified
    if [ "$BUILD_FILE" = "Containerfile" ]; then
        build_cmd="$build_cmd --dockerfile=Containerfile"
    fi
    
    # Add namespace
    build_cmd="$build_cmd -n $NAMESPACE"
    
    print_info "Command: $build_cmd"
    
    if [ "$DRY_RUN" = false ]; then
        if eval "$build_cmd"; then
            print_success "Build configuration created successfully"
        else
            print_error "Failed to create build configuration"
            exit 1
        fi
    fi
}

# Function to start build
start_build() {
    print_info "Starting build..."
    
    local start_cmd="oc start-build $BUILD_NAME"
    
    # Add from-dir
    start_cmd="$start_cmd --from-dir=."
    
    # Add follow if requested
    if [ "$FOLLOW_BUILD" = true ]; then
        start_cmd="$start_cmd --follow"
    fi
    
    # Add namespace
    start_cmd="$start_cmd -n $NAMESPACE"
    
    print_info "Command: $start_cmd"
    
    if [ "$DRY_RUN" = false ]; then
        if eval "$start_cmd"; then
            print_success "Build started successfully"
        else
            print_error "Failed to start build"
            exit 1
        fi
    fi
}

# Function to verify build
verify_build() {
    if [ "$DRY_RUN" = true ]; then
        return
    fi
    
    print_info "Verifying build..."
    
    # Wait a moment for build to start
    sleep 5
    
    # Check build status
    local build_status=$(oc get builds -n "$NAMESPACE" -l build="$BUILD_NAME" --no-headers -o custom-columns=":status.phase" 2>/dev/null | tail -1)
    
    if [ -n "$build_status" ]; then
        print_info "Build status: $build_status"
        
        case $build_status in
            "Complete")
                print_success "Build completed successfully!"
                ;;
            "Failed")
                print_error "Build failed. Check logs with: oc logs build/$BUILD_NAME-1 -n $NAMESPACE"
                exit 1
                ;;
            "Running"|"Pending")
                print_info "Build is still running. You can follow logs with: oc logs build/$BUILD_NAME-1 -n $NAMESPACE -f"
                ;;
            *)
                print_warning "Build status: $build_status"
                ;;
        esac
    else
        print_warning "Could not determine build status"
    fi
}

# Function to show next steps
show_next_steps() {
    print_info "Next steps:"
    echo
    echo "  # Check build status"
    echo "  oc get builds -n $NAMESPACE"
    echo
    echo "  # Follow build logs"
    echo "  oc logs build/$BUILD_NAME-1 -n $NAMESPACE -f"
    echo
    echo "  # Check build configuration"
    echo "  oc get buildconfig $BUILD_NAME -n $NAMESPACE -o yaml"
    echo
    echo "  # Deploy the application"
    echo "  oc apply -f openshift/deployment.yaml -n $NAMESPACE"
    echo
    echo "  # Or deploy with Helm"
    echo "  helm install rag-api ./helm --namespace $NAMESPACE"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            BUILD_NAME="$2"
            shift 2
            ;;
        -f|--file)
            BUILD_FILE="$2"
            shift 2
            ;;
        -p|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --no-follow)
            FOLLOW_BUILD=false
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
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
    print_info "RAG OpenShift AI API - OpenShift Build Script"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Create build configuration
    create_build_config
    
    # Start build
    start_build
    
    # Verify build
    verify_build
    
    # Show next steps
    show_next_steps
}

# Run main function
main "$@" 