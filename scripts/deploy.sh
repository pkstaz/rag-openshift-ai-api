#!/bin/bash

# =============================================================================
# RAG OpenShift AI API - Deployment Script
# =============================================================================

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
VALUES_FILE="helm/values-examples.yaml"
IMAGE_TAG="latest"
ENVIRONMENT="development"
DEBUG=false
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
    echo "  -f, --values-file FILE       Values file (default: helm/values-examples.yaml)"
    echo "  -t, --image-tag TAG          Image tag override (default: latest)"
    echo "  -e, --environment ENV        Environment: dev, staging, prod (default: dev)"
    echo "  -d, --debug                  Enable debug output"
    echo "  --dry-run                    Validate without deploying"
    echo "  --no-wait                    Don't wait for deployment to be ready"
    echo "  --port-forward               Setup port-forward after deployment"
    echo "  --tail-logs                  Tail logs after deployment"
    echo "  --no-rollback                Don't rollback on failure"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Deploy to development"
    echo "  $0 -e prod -f prod-values.yaml       # Deploy to production"
    echo "  $0 --dry-run --debug                 # Validate deployment"
    echo "  $0 --port-forward --tail-logs        # Deploy with dev features"
}

# Function to cleanup on exit
cleanup() {
    if [[ -n "$PORT_FORWARD_PID" ]]; then
        print_info "Stopping port-forward..."
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

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
        -t|--image-tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        --dry-run)
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

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod"
    exit 1
fi

# Validate values file exists
if [[ ! -f "$VALUES_FILE" ]]; then
    print_error "Values file not found: $VALUES_FILE"
    exit 1
fi

print_info "Starting deployment..."
print_info "Namespace: $NAMESPACE"
print_info "Release: $RELEASE_NAME"
print_info "Environment: $ENVIRONMENT"
print_info "Values file: $VALUES_FILE"
print_info "Image tag: $IMAGE_TAG"

# =============================================================================
# 1. ENVIRONMENT SETUP
# =============================================================================

print_info "Setting up environment..."

# Check required tools
print_info "Checking required tools..."
if ! command -v oc &> /dev/null; then
    print_error "OpenShift CLI (oc) not found. Please install it."
    exit 1
fi

if ! command -v helm &> /dev/null; then
    print_error "Helm not found. Please install it."
    exit 1
fi

print_success "Required tools found"

# Verify OpenShift login
print_info "Verifying OpenShift login..."
if ! oc whoami &> /dev/null; then
    print_error "Not logged into OpenShift. Please run 'oc login' first."
    exit 1
fi

CURRENT_USER=$(oc whoami)
print_success "Logged in as: $CURRENT_USER"

# Check cluster connectivity
print_info "Checking cluster connectivity..."
if ! oc cluster-info &> /dev/null; then
    print_error "Cannot connect to OpenShift cluster"
    exit 1
fi

CLUSTER_URL=$(oc config view --minify -o jsonpath='{.clusters[0].cluster.server}')
print_success "Connected to cluster: $CLUSTER_URL"

# =============================================================================
# 2. NAMESPACE MANAGEMENT
# =============================================================================

print_info "Managing namespace..."

# Check if namespace exists
if ! oc get namespace "$NAMESPACE" &> /dev/null; then
    print_info "Creating namespace: $NAMESPACE"
    oc new-project "$NAMESPACE" --display-name="RAG OpenShift AI API" --description="RAG OpenShift AI API deployment"
    
    # Set namespace labels
    oc label namespace "$NAMESPACE" \
        environment="$ENVIRONMENT" \
        app.kubernetes.io/name="rag-openshift-ai-api" \
        app.kubernetes.io/part-of="rag-system"
    
    print_success "Namespace created with labels"
else
    print_info "Namespace exists: $NAMESPACE"
    
    # Update labels if needed
    oc label namespace "$NAMESPACE" \
        environment="$ENVIRONMENT" \
        app.kubernetes.io/name="rag-openshift-ai-api" \
        app.kubernetes.io/part-of="rag-system" \
        --overwrite
fi

# Switch to namespace
oc project "$NAMESPACE"

# =============================================================================
# 3. PRE-DEPLOYMENT CHECKS
# =============================================================================

print_info "Running pre-deployment checks..."

# Check if Helm chart exists
if [[ ! -d "helm" ]]; then
    print_error "Helm chart directory not found"
    exit 1
fi

# Validate Helm chart
print_info "Validating Helm chart..."
if ! helm lint helm; then
    print_error "Helm chart validation failed"
    exit 1
fi

print_success "Helm chart is valid"

# Check resource quotas (if any)
print_info "Checking resource quotas..."
if oc get resourcequota -n "$NAMESPACE" 2>/dev/null; then
    print_info "Resource quotas found, checking availability..."
    # This is a basic check - in production you might want more detailed validation
fi

# =============================================================================
# 4. HELM DEPLOYMENT
# =============================================================================

print_info "Starting Helm deployment..."

# Prepare Helm command
HELM_CMD="helm upgrade --install $RELEASE_NAME ./helm"

# Add values file
HELM_CMD="$HELM_CMD -f $VALUES_FILE"

# Add image tag override
if [[ "$IMAGE_TAG" != "latest" ]]; then
    HELM_CMD="$HELM_CMD --set image.tag=$IMAGE_TAG"
fi

# Add environment-specific overrides
case "$ENVIRONMENT" in
    "dev")
        HELM_CMD="$HELM_CMD --set replicaCount=1 --set config.api.debug=true"
        ;;
    "staging")
        HELM_CMD="$HELM_CMD --set replicaCount=2 --set config.api.debug=false"
        ;;
    "prod")
        HELM_CMD="$HELM_CMD --set replicaCount=3 --set config.api.debug=false --set networkPolicy.enabled=true"
        ;;
esac

# Add dry-run if requested
if [[ "$DRY_RUN" == true ]]; then
    HELM_CMD="$HELM_CMD --dry-run"
    print_info "DRY RUN MODE - No actual deployment will be performed"
fi

# Add wait flag
if [[ "$WAIT_FOR_READY" == true ]]; then
    HELM_CMD="$HELM_CMD --wait --timeout=10m"
fi

# Add atomic flag for rollback
if [[ "$ROLLBACK_ON_FAILURE" == true ]]; then
    HELM_CMD="$HELM_CMD --atomic"
fi

# Add debug if requested
if [[ "$DEBUG" == true ]]; then
    HELM_CMD="$HELM_CMD --debug"
fi

print_info "Executing: $HELM_CMD"

# Execute deployment
if eval $HELM_CMD; then
    print_success "Helm deployment completed successfully!"
else
    print_error "Helm deployment failed!"
    if [[ "$ROLLBACK_ON_FAILURE" == true && "$DRY_RUN" == false ]]; then
        print_info "Rollback will be attempted automatically due to --atomic flag"
    fi
    exit 1
fi

# =============================================================================
# 5. POST-DEPLOYMENT VALIDATION
# =============================================================================

if [[ "$DRY_RUN" == false ]]; then
    print_info "Running post-deployment validation..."
    
    # Wait for pods to be ready
    print_info "Waiting for pods to be ready..."
    if oc wait --for=condition=ready pod -l app.kubernetes.io/name=rag-openshift-ai-api -n "$NAMESPACE" --timeout=300s; then
        print_success "All pods are ready"
    else
        print_warning "Some pods may not be ready yet"
    fi
    
    # Get pod status
    print_info "Pod status:"
    oc get pods -n "$NAMESPACE" -l app.kubernetes.io/name=rag-openshift-ai-api
    
    # Check service
    print_info "Service status:"
    oc get svc -n "$NAMESPACE" -l app.kubernetes.io/name=rag-openshift-ai-api
    
    # Check route
    print_info "Route status:"
    oc get route -n "$NAMESPACE" -l app.kubernetes.io/name=rag-openshift-ai-api
    
    # Health check
    print_info "Performing health check..."
    ROUTE_URL=$(oc get route "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
    
    if [[ -n "$ROUTE_URL" ]]; then
        print_info "Route URL: https://$ROUTE_URL"
        
        # Wait a bit for route to be ready
        sleep 10
        
        if curl -f -k "https://$ROUTE_URL/health" &> /dev/null; then
            print_success "Health check passed"
        else
            print_warning "Health check failed - route may still be initializing"
        fi
    else
        print_warning "No route found - health check skipped"
    fi
fi

# =============================================================================
# 6. DEVELOPMENT FEATURES
# =============================================================================

if [[ "$DRY_RUN" == false ]]; then
    # Port-forward setup
    if [[ "$PORT_FORWARD" == true ]]; then
        print_info "Setting up port-forward..."
        oc port-forward svc/"$RELEASE_NAME" 8000:8000 -n "$NAMESPACE" &
        PORT_FORWARD_PID=$!
        sleep 2
        print_success "Port-forward active: http://localhost:8000"
    fi
    
    # Log tailing
    if [[ "$TAIL_LOGS" == true ]]; then
        print_info "Tailing logs (Ctrl+C to stop)..."
        oc logs -f deployment/"$RELEASE_NAME" -n "$NAMESPACE"
    fi
fi

# =============================================================================
# 7. OUTPUT INFORMATION
# =============================================================================

print_success "Deployment completed successfully!"
echo ""
echo "=== DEPLOYMENT SUMMARY ==="
echo "Namespace: $NAMESPACE"
echo "Release: $RELEASE_NAME"
echo "Environment: $ENVIRONMENT"
echo ""

if [[ "$DRY_RUN" == false ]]; then
    echo "=== ACCESS INFORMATION ==="
    
    # Service information
    SERVICE_IP=$(oc get svc "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    echo "Service IP: $SERVICE_IP"
    echo "Service Port: 8000"
    
    # Route information
    if [[ -n "$ROUTE_URL" ]]; then
        echo "Route URL: https://$ROUTE_URL"
        echo "Health Check: https://$ROUTE_URL/health"
        echo "API Docs: https://$ROUTE_URL/docs"
        echo "Metrics: https://$ROUTE_URL/api/v1/metrics"
    fi
    
    # Port-forward information
    if [[ "$PORT_FORWARD" == true ]]; then
        echo "Local Access: http://localhost:8000"
    fi
    
    echo ""
    echo "=== USEFUL COMMANDS ==="
    echo "View logs: oc logs -f deployment/$RELEASE_NAME -n $NAMESPACE"
    echo "Check status: oc get pods -n $NAMESPACE"
    echo "Access shell: oc rsh deployment/$RELEASE_NAME -n $NAMESPACE"
    echo "View events: oc get events -n $NAMESPACE"
    echo "Delete release: helm uninstall $RELEASE_NAME -n $NAMESPACE"
fi

echo ""
print_success "Deployment script completed!" 