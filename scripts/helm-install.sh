#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - Helm Installation Script
# =============================================================================
# Automated Helm deployment for OpenShift/Kubernetes

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
VALUES_FILE="helm/values.yaml"
DRY_RUN=false
WAIT_FOR_READY=true
PORT_FORWARD=false
TAIL_LOGS=false
ROLLBACK_ON_FAILURE=true

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
    echo "  -f, --values-file FILE       Values file (default: helm/values.yaml)"
    echo "  -d, --dry-run                Validate without deploying"
    echo "  --no-wait                    Don't wait for deployment to be ready"
    echo "  --port-forward               Setup port-forward after deployment"
    echo "  --tail-logs                  Tail logs after deployment"
    echo "  --no-rollback                Don't rollback on failure"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Deploy with default settings"
    echo "  $0 -n my-namespace -r my-release      # Custom namespace and release"
    echo "  $0 --dry-run                          # Validate deployment"
    echo "  $0 --port-forward --tail-logs         # Deploy with dev features"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed. Please install Helm 3.x first."
        exit 1
    fi
    
    # Check Helm version
    HELM_VERSION=$(helm version --short | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$HELM_VERSION" -lt 3 ]; then
        print_error "Helm 3.x is required. Current version: $(helm version --short)"
        exit 1
    fi
    
    # Check if OpenShift CLI is available
    if ! command -v oc &> /dev/null; then
        print_warning "OpenShift CLI (oc) not found. Some features may not work."
    else
        # Check if logged in to OpenShift
        if ! oc whoami &> /dev/null; then
            print_warning "Not logged in to OpenShift. Please run 'oc login' first."
        fi
    fi
    
    # Check if Helm chart exists
    if [ ! -d "helm" ]; then
        print_error "Helm chart not found at: helm"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

# Function to create namespace
create_namespace() {
    print_info "Creating namespace: $NAMESPACE"
    
    if command -v oc &> /dev/null; then
        # Use OpenShift CLI
        if oc get project "$NAMESPACE" &> /dev/null; then
            print_info "Namespace $NAMESPACE already exists"
        else
            oc new-project "$NAMESPACE"
            print_success "Created namespace: $NAMESPACE"
        fi
    else
        # Use kubectl
        if kubectl get namespace "$NAMESPACE" &> /dev/null; then
            print_info "Namespace $NAMESPACE already exists"
        else
            kubectl create namespace "$NAMESPACE"
            print_success "Created namespace: $NAMESPACE"
        fi
    fi
}

# Function to get values file path
get_values_file() {
    if [ -n "$VALUES_FILE" ]; then
        # Use custom values file
        if [ ! -f "$VALUES_FILE" ]; then
            print_error "Custom values file not found: $VALUES_FILE"
            exit 1
        fi
        echo "$VALUES_FILE"
    else
        # Use examples file with deployment type
        EXAMPLES_FILE="helm/values-examples.yaml"
        if [ ! -f "$EXAMPLES_FILE" ]; then
            print_error "Values examples file not found: $EXAMPLES_FILE"
            exit 1
        fi
        echo "$EXAMPLES_FILE"
    fi
}

# Function to build Helm command
build_helm_command() {
    local cmd="helm install $RELEASE_NAME helm"
    
    # Add namespace
    cmd="$cmd --namespace $NAMESPACE"
    
    # Add values file
    local values_file=$(get_values_file)
    if [ -n "$VALUES_FILE" ]; then
        cmd="$cmd --values $values_file"
    else
        cmd="$cmd --values $values_file --set-string config=development"
    fi
    
    # Add dry run if requested
    if [ "$DRY_RUN" = true ]; then
        cmd="$cmd --dry-run"
    fi
    
    echo "$cmd"
}

# Function to install Helm chart
install_helm_chart() {
    print_info "Installing Helm chart..."
    
    local helm_cmd=$(build_helm_command)
    print_info "Command: $helm_cmd"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry run mode - no changes will be made"
        eval "$helm_cmd"
    else
        if [ "$WAIT_FOR_READY" = true ]; then
            echo
            print_warning "This will install the RAG API in namespace: $NAMESPACE"
            print_warning "Release name: $RELEASE_NAME"
            echo
            read -p "Do you want to continue? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Installation cancelled"
                exit 0
            fi
        fi
        
        # Execute Helm command
        if eval "$helm_cmd"; then
            print_success "Helm chart installed successfully"
        else
            print_error "Failed to install Helm chart"
            exit 1
        fi
    fi
}

# Function to verify installation
verify_installation() {
    if [ "$DRY_RUN" = true ]; then
        return
    fi
    
    print_info "Verifying installation..."
    
    # Wait for deployment to be ready
    print_info "Waiting for deployment to be ready..."
    if command -v oc &> /dev/null; then
        oc rollout status deployment/"$RELEASE_NAME" -n "$NAMESPACE" --timeout=300s
    else
        kubectl rollout status deployment/"$RELEASE_NAME" -n "$NAMESPACE" --timeout=300s
    fi
    
    # Check pod status
    print_info "Checking pod status..."
    if command -v oc &> /dev/null; then
        oc get pods -l app.kubernetes.io/name="$RELEASE_NAME" -n "$NAMESPACE"
    else
        kubectl get pods -l app.kubernetes.io/name="$RELEASE_NAME" -n "$NAMESPACE"
    fi
    
    # Get service URL
    print_info "Getting service information..."
    if command -v oc &> /dev/null; then
        oc get route "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null || print_warning "Route not found"
    fi
    
    print_success "Installation verification completed"
}

# Function to show post-installation info
show_post_installation_info() {
    if [ "$DRY_RUN" = true ]; then
        return
    fi
    
    echo
    print_success "RAG API installation completed!"
    echo
    print_info "Next steps:"
    echo "1. Configure ElasticSearch and vLLM endpoints"
    echo "2. Test the API endpoints"
    echo "3. Set up monitoring and alerting"
    echo
    print_info "Useful commands:"
    echo "  # Check deployment status"
    echo "  helm status $RELEASE_NAME -n $NAMESPACE"
    echo
    echo "  # View logs"
    echo "  oc logs -l app.kubernetes.io/name=$RELEASE_NAME -n $NAMESPACE"
    echo
    echo "  # Get service URL"
    echo "  oc get route $RELEASE_NAME -n $NAMESPACE"
    echo
    echo "  # Upgrade deployment"
    echo "  helm upgrade $RELEASE_NAME helm -n $NAMESPACE"
    echo
    echo "  # Uninstall deployment"
    echo "  helm uninstall $RELEASE_NAME -n $NAMESPACE"
    echo
    print_info "Documentation:"
    echo "  - Helm Installation Guide: docs/HELM_INSTALLATION.md"
    echo "  - API Documentation: docs/api.md"
    echo "  - Troubleshooting: README.md#troubleshooting"
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
        -f|--values-file)
            VALUES_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-wait)
            WAIT_FOR_READY=false
            shift
            ;;
        --port-forward)
            PORT_FORWARD=true
            shift
            ;;
        --tail-logs)
            TAIL_LOGS=true
            shift
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE=false
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
    print_info "RAG OpenShift AI API - Helm Installation Script"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Create namespace
    create_namespace
    
    # Install Helm chart
    install_helm_chart
    
    # Verify installation
    verify_installation
    
    # Show post-installation info
    show_post_installation_info
}

# Run main function
main "$@" 