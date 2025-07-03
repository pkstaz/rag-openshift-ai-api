#!/bin/bash

# =============================================================================
# Quick Deploy Script for RAG OpenShift AI API
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Default values
NAMESPACE=${1:-"rag-project"}
ELASTICSEARCH_URL=${2:-"http://elasticsearch:9200"}
VLLM_URL=${3:-"http://vllm-server:8001"}

print_info "Quick Deploy RAG OpenShift AI API"
print_info "Namespace: $NAMESPACE"
print_info "ElasticSearch: $ELASTICSEARCH_URL"
print_info "vLLM: $VLLM_URL"

# Check if oc is available
if ! command -v oc &> /dev/null; then
    echo "Error: OpenShift CLI (oc) is not installed"
    exit 1
fi

# Check if logged in
if ! oc whoami &> /dev/null; then
    echo "Error: Not logged in to OpenShift. Run: oc login"
    exit 1
fi

# Create namespace if it doesn't exist
if ! oc get namespace $NAMESPACE &> /dev/null; then
    print_info "Creating namespace: $NAMESPACE"
    oc new-project $NAMESPACE --display-name="RAG API Project"
fi

# Deploy using oc new-app
print_info "Deploying application..."
oc new-app \
    --name=rag-api \
    --strategy=docker \
    --dockerfile=Containerfile \
    --source=https://github.com/your-repo/rag-openshift-ai-api.git \
    --context-dir=. \
    -n $NAMESPACE

# Set environment variables
print_info "Configuring environment variables..."
oc set env dc/rag-api \
    ELASTICSEARCH_URL=$ELASTICSEARCH_URL \
    VLLM_URL=$VLLM_URL \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production \
    -n $NAMESPACE

# Set resource limits
print_info "Setting resource limits..."
oc set resources dc/rag-api \
    --requests=cpu=500m,memory=1Gi \
    --limits=cpu=2000m,memory=4Gi \
    -n $NAMESPACE

# Add health checks
print_info "Adding health checks..."
oc set probe dc/rag-api \
    --liveness \
    --get-url=http://:8000/health \
    --initial-delay-seconds=60 \
    --period-seconds=30 \
    -n $NAMESPACE

oc set probe dc/rag-api \
    --readiness \
    --get-url=http://:8000/ready \
    --initial-delay-seconds=30 \
    --period-seconds=10 \
    -n $NAMESPACE

# Expose service
print_info "Exposing service..."
oc expose dc/rag-api --port=8000 -n $NAMESPACE
oc expose svc/rag-api -n $NAMESPACE

# Wait for deployment
print_info "Waiting for deployment to complete..."
oc rollout status dc/rag-api -n $NAMESPACE --timeout=10m

# Get route URL
ROUTE_URL=$(oc get route rag-api -n $NAMESPACE -o jsonpath='{.spec.host}')

print_success "Deployment completed!"
echo ""
echo "Application Information:"
echo "  Namespace: $NAMESPACE"
echo "  Route: https://$ROUTE_URL"
echo "  API Docs: https://$ROUTE_URL/docs"
echo "  Health Check: https://$ROUTE_URL/health"
echo "  Metrics: https://$ROUTE_URL/metrics"
echo ""
echo "Useful commands:"
echo "  oc logs -f dc/rag-api -n $NAMESPACE    # View logs"
echo "  oc get pods -n $NAMESPACE              # List pods"
echo "  oc get route rag-api -n $NAMESPACE     # Get route info" 