#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - Helm Installation Script
# =============================================================================
# This script provides easy Helm installation for different deployment scenarios

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
VALUES_FILE=""
DEPLOYMENT_TYPE="development"
HELM_CHART_PATH="./helm"
DRY_RUN=false
FORCE=false

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
    -n, --namespace NAME       Namespace to deploy to (default: rag-openshift-ai)
    -r, --release NAME         Helm release name (default: rag-api)
    -t, --type TYPE            Deployment type: development, production, ha, multi-tenant, edge, testing (default: development)
    -v, --values FILE          Custom values file path
    -c, --chart PATH           Helm chart path (default: ./helm)
    -d, --dry-run              Dry run mode (don't actually install)
    -f, --force                Force installation (skip confirmation)
    -h, --help                 Show this help message

Deployment Types:
    development     - Single replica, minimal resources, debug enabled
    production      - Multiple replicas, production resources, monitoring enabled
    ha              - High availability deployment with 5+ replicas
    multi-tenant    - Multi-tenant configuration with rate limiting
    edge            - Edge/remote deployment with limited resources
    testing         - Testing/CI deployment with relaxed security

Examples:
    # Install development deployment
    $0 -t development

    # Install production deployment with custom namespace
    $0 -t production -n rag-prod -r rag-api-prod

    # Install with custom values file
    $0 -v custom-values.yaml

    # Dry run to see what would be installed
    $0 -t production -d

EOF
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
    if [ ! -d "$HELM_CHART_PATH" ]; then
        print_error "Helm chart not found at: $HELM_CHART_PATH"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

# Function to validate deployment type
validate_deployment_type() {
    case $DEPLOYMENT_TYPE in
        development|production|ha|multi-tenant|edge|testing)
            print_info "Deployment type: $DEPLOYMENT_TYPE"
            ;;
        *)
            print_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            show_usage
            exit 1
            ;;
    esac
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
        EXAMPLES_FILE="$HELM_CHART_PATH/values-examples.yaml"
        if [ ! -f "$EXAMPLES_FILE" ]; then
            print_error "Values examples file not found: $EXAMPLES_FILE"
            exit 1
        fi
        echo "$EXAMPLES_FILE"
    fi
}

# Function to build Helm command
build_helm_command() {
    local cmd="helm install $RELEASE_NAME $HELM_CHART_PATH"
    
    # Add namespace
    cmd="$cmd --namespace $NAMESPACE"
    
    # Add values file
    local values_file=$(get_values_file)
    if [ -n "$VALUES_FILE" ]; then
        cmd="$cmd --values $values_file"
    else
        cmd="$cmd --values $values_file --set-string config=$DEPLOYMENT_TYPE"
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
        if [ "$FORCE" = false ]; then
            echo
            print_warning "This will install the RAG API in namespace: $NAMESPACE"
            print_warning "Release name: $RELEASE_NAME"
            print_warning "Deployment type: $DEPLOYMENT_TYPE"
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
    echo "  helm upgrade $RELEASE_NAME $HELM_CHART_PATH -n $NAMESPACE"
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
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -v|--values)
            VALUES_FILE="$2"
            shift 2
            ;;
        -c|--chart)
            HELM_CHART_PATH="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
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
    
    # Validate inputs
    validate_deployment_type
    
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