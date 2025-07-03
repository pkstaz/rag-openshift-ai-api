# Containerfile Documentation

## Overview

This Containerfile creates a production-ready container for the RAG OpenShift AI API, optimized for OpenShift deployment with security best practices.

## Features

### 🔒 Security Features
- **Non-root user**: Runs as `rag-api` user (UID 1001)
- **OpenShift compatible**: Supports random UID assignment
- **Minimal attack surface**: Based on slim Python image
- **Proper file permissions**: All files owned by non-root user

### 🚀 Performance Optimizations
- **Multi-stage build**: Reduces final image size
- **Layer caching**: Dependencies installed before code copy
- **Model pre-loading**: Sentence transformers model cached at build time
- **No cache pip**: Reduces image size

### 🛠️ Development Support
- **Development target**: Includes testing and development tools
- **Hot reload**: Development mode with auto-reload
- **Debug endpoints**: Additional debugging information

## Build Stages

### Stage 1: Base
- Python 3.11-slim base image
- System dependencies (curl, gcc, g++)
- Non-root user creation

### Stage 2: Dependencies
- Python dependencies installation
- Layer caching optimization

### Stage 3: Models
- Sentence transformers model pre-download
- Model caching in `/opt/models`

### Stage 4: Application
- Application code copy
- Directory structure setup

### Stage 5: Production
- Final production image
- Health checks and runtime configuration

### Stage 6: Development (Optional)
- Development dependencies
- Testing tools

## Building the Container

### Using the Build Script

```bash
# Build production image
./scripts/build.sh

# Build with specific tag
./scripts/build.sh -t v1.0.0

# Build development image
./scripts/build.sh -T development

# Build for specific platform
./scripts/build.sh -p linux/arm64

# Build and push to registry
./scripts/build.sh -n my-registry/rag-api --push
```

### Manual Build

```bash
# Production build
buildah build --target production -t rag-openshift-ai-api:latest .

# Development build
buildah build --target development -t rag-openshift-ai-api:dev .

# Multi-platform build
buildah build --platform linux/amd64,linux/arm64 -t rag-openshift-ai-api:latest .
```

### Using Docker (if available)

```bash
# Production build
docker build --target production -t rag-openshift-ai-api:latest .

# Development build
docker build --target development -t rag-openshift-ai-api:dev .
```

## Running the Container

### Local Development

```bash
# Run production container
podman run -p 8000:8000 rag-openshift-ai-api:latest

# Run development container
podman run -p 8000:8000 rag-openshift-ai-api:dev

# Run with environment variables
podman run -p 8000:8000 \
  -e ELASTICSEARCH_URL=http://localhost:9200 \
  -e VLLM_URL=http://localhost:8001 \
  rag-openshift-ai-api:latest
```

### OpenShift Deployment

```bash
# Build and push to OpenShift registry
./scripts/build.sh -n image-registry.openshift-image-registry.svc:5000/rag-project/rag-api --push

# Deploy using oc
oc new-app --image-stream=rag-api:latest --name=rag-api
```

## Environment Variables

The container supports the following environment variables:

### API Configuration
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `API_VERSION`: API version (default: 0.1.0)

### ElasticSearch
- `ELASTICSEARCH_URL`: ElasticSearch URL
- `ELASTICSEARCH_USERNAME`: ElasticSearch username
- `ELASTICSEARCH_PASSWORD`: ElasticSearch password

### vLLM
- `VLLM_URL`: vLLM server URL
- `VLLM_MODEL_NAME`: Model name to use

### Embeddings
- `EMBEDDING_MODEL_NAME`: Sentence transformers model name
- `EMBEDDING_DEVICE`: Device to use (cpu/cuda)

### Logging
- `LOG_LEVEL`: Logging level (INFO/DEBUG/WARNING/ERROR)

## Health Checks

The container includes health checks:

```bash
# Health check endpoint
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready

# Metrics endpoint
curl http://localhost:8000/metrics
```

## Security Considerations

### OpenShift Security Context

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

### Network Policies

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
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Check file permissions
   podman exec -it container_name ls -la /app
   ```

2. **Model Loading Issues**
   ```bash
   # Check model directory
   podman exec -it container_name ls -la /opt/models
   ```

3. **Health Check Failures**
   ```bash
   # Check container logs
   podman logs container_name
   
   # Check health endpoint
   podman exec -it container_name curl localhost:8000/health
   ```

### Debug Mode

For debugging, use the development target:

```bash
# Build development image
./scripts/build.sh -T development

# Run with debug endpoints
podman run -p 8000:8000 rag-openshift-ai-api:dev

# Access debug endpoints
curl http://localhost:8000/debug/info
curl http://localhost:8000/debug/settings
```

## Best Practices

1. **Always use specific tags** instead of `latest`
2. **Scan images for vulnerabilities** before deployment
3. **Use resource limits** in OpenShift deployments
4. **Monitor container health** using provided endpoints
5. **Backup models** if using custom embeddings
6. **Use secrets** for sensitive configuration

## Image Size Optimization

The multi-stage build reduces image size by:
- Excluding development dependencies in production
- Using slim base image
- Removing package cache
- Optimizing layer order

Expected image sizes:
- Production: ~2-3GB
- Development: ~3-4GB 