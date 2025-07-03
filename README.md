# RAG OpenShift AI API

A Retrieval-Augmented Generation (RAG) API service designed for enterprise environments running on OpenShift. This service combines vector search with large language models to provide accurate, contextual responses to user queries.

## 🚀 Features

- **Vector Search**: Semantic document retrieval using ElasticSearch
- **Text Generation**: AI-powered response generation using vLLM
- **Metadata Filtering**: Advanced filtering capabilities for precise results
- **Enterprise Ready**: OpenShift-native deployment with security and monitoring
- **Scalable**: Horizontal scaling and load balancing support
- **Observability**: Prometheus metrics, structured logging, health checks

## 📋 Prerequisites

- OpenShift 4.x cluster with admin access
- ElasticSearch 8.x instance (local or cloud)
- vLLM server running with compatible models
- `oc` CLI tool installed and configured
- `podman` or `docker` for container builds

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │    │   RAG API       │    │   ElasticSearch │
│                 │◄──►│   (FastAPI)     │◄──►│   (Vector DB)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   vLLM Server   │
                       │   (LLM Models)  │
                       └─────────────────┘
```

## 🛠️ Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic
- **Vector Database**: ElasticSearch 8.x
- **LLM Server**: vLLM with HuggingFace models
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Monitoring**: Prometheus metrics, structured logging
- **Deployment**: OpenShift, Kubernetes
- **Testing**: pytest, integration tests, load testing

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/rag-openshift-ai-api.git
cd rag-openshift-ai-api
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-xdist pytest-html
```

### 3. Environment Configuration

Create a `.env` file with your configuration:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
API_LOG_LEVEL=INFO

# ElasticSearch Configuration
ES_URL=http://localhost:9200
ES_INDEX_NAME=rag_documents
ES_USERNAME=elastic
ES_PASSWORD=your-password
ES_TIMEOUT=30
ES_VECTOR_DIMENSION=384

# vLLM Configuration
VLLM_URL=http://localhost:8001
VLLM_MODEL_NAME=microsoft/DialoGPT-medium
VLLM_TIMEOUT=60
VLLM_TEMPERATURE=0.7
VLLM_MAX_TOKENS=512

# Embedding Configuration
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32

# RAG Configuration
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_SEARCH_TYPE=vector
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200

# Environment Configuration
ENV_ENVIRONMENT=production
ENV_METRICS_ENABLED=true
ENV_SECRET_KEY=your-secret-key-change-in-production
```

## 🚀 Manual Deployment

### 1. Build Container Image

```bash
# Build the container image
podman build -t rag-api:latest .

# Tag for your registry (replace with your registry)
podman tag rag-api:latest your-registry.com/rag-api:latest

# Push to registry
podman push your-registry.com/rag-api:latest
```

### 2. Create OpenShift Project

```bash
# Create new project
oc new-project rag-demo

# Or use existing project
oc project rag-demo
```

### 3. Create ServiceAccount

```bash
# Create ServiceAccount
oc create serviceaccount rag-api-sa

# Add any required permissions
oc adm policy add-scc-to-user anyuid -z rag-api-sa
```

### 4. Create ConfigMap

```bash
# Create ConfigMap for application configuration
oc create configmap rag-api-config \
  --from-literal=API_HOST=0.0.0.0 \
  --from-literal=API_PORT=8000 \
  --from-literal=API_DEBUG=false \
  --from-literal=API_LOG_LEVEL=INFO \
  --from-literal=ES_URL=http://elasticsearch:9200 \
  --from-literal=ES_INDEX_NAME=rag_documents \
  --from-literal=VLLM_URL=http://vllm-server:8001 \
  --from-literal=VLLM_MODEL_NAME=microsoft/DialoGPT-medium \
  --from-literal=EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2 \
  --from-literal=RAG_TOP_K=5 \
  --from-literal=ENV_ENVIRONMENT=production
```

### 5. Create Secret

```bash
# Create Secret for sensitive data
oc create secret generic rag-api-secret \
  --from-literal=ES_USERNAME=elastic \
  --from-literal=ES_PASSWORD=your-password \
  --from-literal=ENV_SECRET_KEY=your-secret-key-change-in-production
```

### 6. Create Deployment

```bash
# Create Deployment
oc create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
  labels:
    app: rag-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
    spec:
      serviceAccountName: rag-api-sa
      containers:
      - name: rag-api
        image: your-registry.com/rag-api:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: rag-api-config
        - secretRef:
            name: rag-api-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1001
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
EOF
```

### 7. Create Service

```bash
# Create Service
oc create -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: rag-api
  labels:
    app: rag-api
spec:
  selector:
    app: rag-api
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  type: ClusterIP
EOF
```

### 8. Create Route

```bash
# Create Route for external access
oc create -f - <<EOF
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: rag-api
  labels:
    app: rag-api
spec:
  host: rag-api-rag-demo.apps.your-cluster.com
  to:
    kind: Service
    name: rag-api
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF
```

### 9. Create HorizontalPodAutoscaler

```bash
# Create HPA for automatic scaling
oc create -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF
```

### 10. Create NetworkPolicy

```bash
# Create NetworkPolicy for security
oc create -f - <<EOF
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
          name: allowed-namespace
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: elasticsearch-namespace
    ports:
    - protocol: TCP
      port: 9200
  - to:
    - namespaceSelector:
        matchLabels:
          name: vllm-namespace
    ports:
    - protocol: TCP
      port: 8001
EOF
```

### 11. Verify Deployment

```bash
# Check deployment status
oc get deployment rag-api

# Check pods
oc get pods -l app=rag-api

# Check service
oc get service rag-api

# Check route
oc get route rag-api

# Check logs
oc logs -l app=rag-api --tail=50
```

## 🧪 Testing

### Run Unit Tests

```bash
# Run unit tests
pytest tests/test_api.py -v

# Run with coverage
pytest tests/test_api.py --cov=src --cov-report=html
```

### Run Integration Tests

```bash
# Run integration tests (requires services)
pytest tests/integration/ -v

# Run specific test categories
pytest tests/integration/ -m "elasticsearch" -v
pytest tests/integration/ -m "vllm" -v
pytest tests/integration/ -m "performance" -v
```

### API Testing

```bash
# Quick health check
curl http://localhost:8000/health

# Basic query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'

# With filters
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Kubernetes platform",
    "top_k": 2,
    "filters": {
      "category": "cloud"
    }
  }'
```

## 📊 Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready

# API info
curl http://localhost:8000/api/v1/info
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/api/v1/metrics

# Specific metrics
curl http://localhost:8000/api/v1/metrics | grep rag_api_requests_total
curl http://localhost:8000/api/v1/metrics | grep rag_api_request_duration_seconds
```

### Logs

```bash
# View application logs
oc logs -l app=rag-api --tail=100

# Follow logs
oc logs -l app=rag-api -f

# Logs with timestamps
oc logs -l app=rag-api --timestamps
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Host to bind the server | `0.0.0.0` |
| `API_PORT` | Port to bind the server | `8000` |
| `API_DEBUG` | Debug mode | `false` |
| `ES_URL` | ElasticSearch URL | `http://localhost:9200` |
| `ES_INDEX_NAME` | Index name for documents | `rag_documents` |
| `VLLM_URL` | vLLM server URL | `http://localhost:8001` |
| `VLLM_MODEL_NAME` | Default model name | `microsoft/DialoGPT-medium` |
| `EMBEDDING_MODEL_NAME` | Embedding model name | `sentence-transformers/all-MiniLM-L6-v2` |
| `RAG_TOP_K` | Number of documents to retrieve | `5` |

### Resource Requirements

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| RAG API | 250m | 500m | 512Mi | 1Gi |
| ElasticSearch | 500m | 1000m | 1Gi | 2Gi |
| vLLM Server | 1000m | 2000m | 2Gi | 4Gi |

## 🔒 Security

### Network Policies

The deployment includes NetworkPolicies to restrict access:

- Ingress: Only from allowed namespaces
- Egress: Only to ElasticSearch and vLLM services

### Security Context

- Non-root user (UID 1001)
- Read-only root filesystem
- No privilege escalation

### Secrets Management

- ElasticSearch credentials stored in Secrets
- Application secrets encrypted at rest
- No hardcoded credentials in code

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale manually
oc scale deployment rag-api --replicas=5

# Check HPA status
oc get hpa rag-api-hpa

# View scaling events
oc describe hpa rag-api-hpa
```

### Vertical Scaling

```bash
# Update resource limits
oc patch deployment rag-api -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "rag-api",
          "resources": {
            "requests": {"memory": "1Gi", "cpu": "500m"},
            "limits": {"memory": "2Gi", "cpu": "1000m"}
          }
        }]
      }
    }
  }
}'
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Pod Not Starting

```bash
# Check pod status
oc get pods -l app=rag-api

# Check pod events
oc describe pod <pod-name>

# Check logs
oc logs <pod-name>
```

#### 2. Service Unavailable

```bash
# Check service endpoints
oc get endpoints rag-api

# Test service connectivity
oc exec <pod-name> -- curl http://rag-api:8000/health

# Check route
oc get route rag-api -o yaml
```

#### 3. High Resource Usage

```bash
# Check resource usage
oc top pods -l app=rag-api

# Check resource limits
oc describe pod <pod-name> | grep -A 10 "Limits:"
```

#### 4. Connection Issues

```bash
# Test ElasticSearch connection
oc exec <pod-name> -- curl http://elasticsearch:9200/_cluster/health

# Test vLLM connection
oc exec <pod-name> -- curl http://vllm-server:8001/v1/models
```

### Debug Commands

```bash
# Enable debug logging
oc set env deployment/rag-api API_DEBUG=true

# Restart deployment
oc rollout restart deployment rag-api

# Check rollout status
oc rollout status deployment rag-api

# Rollback if needed
oc rollout undo deployment rag-api
```

## 📚 API Documentation

For detailed API documentation, see [docs/api.md](docs/api.md).

### Quick API Examples

```bash
# Health check
curl https://rag-api-rag-demo.apps.your-cluster.com/health

# Query with authentication (if enabled)
curl -X POST https://rag-api-rag-demo.apps.your-cluster.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'

# Get metrics
curl https://rag-api-rag-demo.apps.your-cluster.com/api/v1/metrics
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
flake8 src/ tests/

# Run type checking
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/rag-openshift-ai-api/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/rag-openshift-ai-api/discussions)

## 🔗 Related Projects

- [ElasticSearch](https://www.elastic.co/elasticsearch/)
- [vLLM](https://github.com/vllm-project/vllm)
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift)
