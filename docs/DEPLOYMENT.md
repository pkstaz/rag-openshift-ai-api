# OpenShift Deployment Guide

## Overview

This guide covers deploying the RAG OpenShift AI API to OpenShift using `oc new-app` with the Containerfile.

## Prerequisites

### Required Tools
- OpenShift CLI (`oc`)
- Access to OpenShift cluster
- Git repository access

### Required Services
- ElasticSearch instance
- vLLM server instance
- OpenShift cluster with sufficient resources

## Quick Start

### 1. Login to OpenShift
```bash
oc login --token=<your-token> --server=<your-server>
```

### 2. Deploy using Script
```bash
# Deploy with default settings
./scripts/deploy.sh

# Deploy with custom settings
./scripts/deploy.sh \
  -n my-project \
  -a my-rag-api \
  -e http://my-elasticsearch:9200 \
  -v http://my-vllm:8001
```

### 3. Manual Deployment
```bash
# Create project
oc new-project rag-project

# Deploy using oc new-app
oc new-app \
  --name=rag-api \
  --strategy=docker \
  --dockerfile=Containerfile \
  --source=https://github.com/your-repo/rag-openshift-ai-api.git \
  --context-dir=.

# Set environment variables
oc set env dc/rag-api \
  ELASTICSEARCH_URL=http://elasticsearch:9200 \
  VLLM_URL=http://vllm-server:8001 \
  LOG_LEVEL=INFO

# Expose service
oc expose dc/rag-api --port=8000
oc expose svc/rag-api
```

## Deployment Options

### Using the Deployment Script

The deployment script provides several options:

```bash
# Basic deployment
./scripts/deploy.sh

# Custom namespace and application name
./scripts/deploy.sh -n my-project -a my-api

# Custom resource configuration
./scripts/deploy.sh -r 3 --cpu-limit=4000m --memory-limit=8Gi

# Custom service URLs
./scripts/deploy.sh \
  -e http://my-elasticsearch:9200 \
  -v http://my-vllm:8001

# Dry run (show what would be deployed)
./scripts/deploy.sh --dry-run

# Clean up and redeploy
./scripts/deploy.sh --cleanup
```

### Using the Template

```bash
# Process and apply the template
oc process -f openshift/deployment.yaml \
  -p APPLICATION_NAME=rag-api \
  -p NAMESPACE=rag-project \
  -p ELASTICSEARCH_URL=http://elasticsearch:9200 \
  -p VLLM_URL=http://vllm-server:8001 \
  | oc apply -f -
```

### Using oc new-app Directly

```bash
# Deploy from Git repository
oc new-app \
  --name=rag-api \
  --strategy=docker \
  --dockerfile=Containerfile \
  --source=https://github.com/your-repo/rag-openshift-ai-api.git \
  --context-dir=. \
  -n rag-project

# Configure the deployment
oc set env dc/rag-api \
  API_HOST=0.0.0.0 \
  API_PORT=8000 \
  ELASTICSEARCH_URL=http://elasticsearch:9200 \
  VLLM_URL=http://vllm-server:8001 \
  LOG_LEVEL=INFO \
  ENVIRONMENT=production

# Set resource limits
oc set resources dc/rag-api \
  --requests=cpu=500m,memory=1Gi \
  --limits=cpu=2000m,memory=4Gi

# Set replicas
oc scale dc/rag-api --replicas=2

# Add health checks
oc set probe dc/rag-api \
  --liveness \
  --get-url=http://:8000/health \
  --initial-delay-seconds=60 \
  --period-seconds=30

oc set probe dc/rag-api \
  --readiness \
  --get-url=http://:8000/ready \
  --initial-delay-seconds=30 \
  --period-seconds=10

# Expose service
oc expose dc/rag-api --port=8000
oc expose svc/rag-api

# Set security context
oc patch dc/rag-api \
  -p '{"spec":{"template":{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":1001,"fsGroup":1001}}}}}'
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_HOST` | API host binding | `0.0.0.0` | No |
| `API_PORT` | API port | `8000` | No |
| `API_VERSION` | API version | `0.1.0` | No |
| `ELASTICSEARCH_URL` | ElasticSearch server URL | - | Yes |
| `ELASTICSEARCH_USERNAME` | ElasticSearch username | - | No |
| `ELASTICSEARCH_PASSWORD` | ElasticSearch password | - | No |
| `VLLM_URL` | vLLM server URL | - | Yes |
| `VLLM_MODEL_NAME` | vLLM model name | `microsoft/DialoGPT-medium` | No |
| `EMBEDDING_MODEL_NAME` | Embedding model name | `all-MiniLM-L6-v2` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ENVIRONMENT` | Environment name | `production` | No |

### Resource Requirements

#### Minimum Requirements
- CPU: 500m (request), 2000m (limit)
- Memory: 1Gi (request), 4Gi (limit)
- Storage: 1Gi for models

#### Recommended Requirements
- CPU: 1000m (request), 4000m (limit)
- Memory: 2Gi (request), 8Gi (limit)
- Storage: 2Gi for models

### Security Configuration

#### Security Context
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  fsGroup: 1001
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

#### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rag-api-network-policy
spec:
  podSelector:
    matchLabels:
      app: rag-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: frontend
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: elasticsearch
      ports:
        - protocol: TCP
          port: 9200
    - to:
        - namespaceSelector:
            matchLabels:
              name: vllm
      ports:
        - protocol: TCP
          port: 8001
```

## Monitoring and Health Checks

### Health Check Endpoints
- **Liveness**: `GET /health` - Basic health check
- **Readiness**: `GET /ready` - Dependencies health check
- **Metrics**: `GET /metrics` - Prometheus metrics

### Health Check Configuration
```bash
# Liveness probe
oc set probe dc/rag-api \
  --liveness \
  --get-url=http://:8000/health \
  --initial-delay-seconds=60 \
  --period-seconds=30 \
  --timeout-seconds=10 \
  --failure-threshold=3

# Readiness probe
oc set probe dc/rag-api \
  --readiness \
  --get-url=http://:8000/ready \
  --initial-delay-seconds=30 \
  --period-seconds=10 \
  --timeout-seconds=5 \
  --failure-threshold=3
```

### Monitoring Integration

#### Prometheus Metrics
The application exposes Prometheus metrics at `/metrics`:
- API request counters
- Response time histograms
- RAG operation metrics
- Component health status

#### Grafana Dashboard
Create a Grafana dashboard to monitor:
- Request rate and latency
- Error rates
- Resource utilization
- RAG pipeline performance

## Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check build logs
oc logs -f bc/rag-api

# Check build status
oc get builds -l buildconfig=rag-api

# Restart build
oc start-build rag-api
```

#### 2. Deployment Failures
```bash
# Check deployment status
oc rollout status dc/rag-api

# Check pod logs
oc logs -f dc/rag-api

# Describe deployment
oc describe dc/rag-api
```

#### 3. Health Check Failures
```bash
# Check health endpoints
oc exec -it $(oc get pods -l app=rag-api -o jsonpath='{.items[0].metadata.name}') \
  curl localhost:8000/health

oc exec -it $(oc get pods -l app=rag-api -o jsonpath='{.items[0].metadata.name}') \
  curl localhost:8000/ready
```

#### 4. Connection Issues
```bash
# Test ElasticSearch connection
oc exec -it $(oc get pods -l app=rag-api -o jsonpath='{.items[0].metadata.name}') \
  curl $ELASTICSEARCH_URL/_cluster/health

# Test vLLM connection
oc exec -it $(oc get pods -l app=rag-api -o jsonpath='{.items[0].metadata.name}') \
  curl $VLLM_URL/health
```

### Debug Commands

```bash
# Get all resources
oc get all -l app=rag-api

# Check events
oc get events --sort-by='.lastTimestamp'

# Check resource usage
oc top pods -l app=rag-api

# Access container shell
oc exec -it $(oc get pods -l app=rag-api -o jsonpath='{.items[0].metadata.name}') -- /bin/bash
```

## Scaling

### Horizontal Pod Autoscaler
```bash
# Create HPA
oc autoscale dc/rag-api \
  --min=2 \
  --max=10 \
  --cpu-percent=70
```

### Manual Scaling
```bash
# Scale to specific number of replicas
oc scale dc/rag-api --replicas=5

# Scale based on CPU usage
oc autoscale dc/rag-api --min=2 --max=10 --cpu-percent=70
```

## Updates and Rollbacks

### Rolling Updates
```bash
# Start new build
oc start-build rag-api

# Watch rollout
oc rollout status dc/rag-api

# Check rollout history
oc rollout history dc/rag-api
```

### Rollbacks
```bash
# Rollback to previous version
oc rollout undo dc/rag-api

# Rollback to specific version
oc rollout undo dc/rag-api --to-revision=2
```

## Cleanup

### Remove Application
```bash
# Remove all resources
oc delete all -l app=rag-api

# Remove specific resources
oc delete dc/rag-api
oc delete svc/rag-api
oc delete route/rag-api
oc delete bc/rag-api
oc delete is/rag-api

# Remove project
oc delete project rag-project
```

### Using Script
```bash
# Clean up using deployment script
./scripts/deploy.sh --cleanup
```

## Best Practices

1. **Use specific image tags** instead of `latest`
2. **Set appropriate resource limits** based on workload
3. **Configure health checks** for all endpoints
4. **Use secrets** for sensitive configuration
5. **Monitor application metrics** and logs
6. **Test deployments** in staging environment first
7. **Use rolling updates** for zero-downtime deployments
8. **Configure backup strategies** for persistent data
9. **Implement proper logging** and monitoring
10. **Follow security best practices** for containerized applications 