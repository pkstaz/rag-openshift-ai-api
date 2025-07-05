# RAG OpenShift AI API

A Retrieval-Augmented Generation (RAG) API service designed for enterprise environments running on OpenShift. This service combines vector search with large language models to provide accurate, contextual responses to user queries.

## 🚀 Features

- **Vector Search**: Semantic document retrieval using ElasticSearch
- **Text Generation**: AI-powered response generation using vLLM
- **Metadata Filtering**: Advanced filtering capabilities for precise results
- **Enterprise Ready**: OpenShift-native deployment with security and monitoring
- **Scalable**: Horizontal scaling and load balancing support
- **Observability**: Prometheus metrics, structured logging, health checks

## 📖 API Documentation

### Main Endpoints

| Method | Endpoint              | Description                                 |
|--------|-----------------------|---------------------------------------------|
| GET    | `/health`             | Health check (API status)                   |
| GET    | `/ready`              | Readiness check (dependencies status)       |
| GET    | `/api/v1/metrics`     | Prometheus metrics for monitoring           |
| GET    | `/api/v1/info`        | API info, version, and available models     |
| POST   | `/api/v1/query`       | Main RAG endpoint: ask questions to the LLM |

### Example: Health Check

```bash
curl http://localhost:8000/health
```

### Example: Query Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'
```

**Sample Response:**
```json
{
  "answer": "OpenShift is a Kubernetes platform that provides enterprise-grade container orchestration capabilities...",
  "sources": [
    {
      "id": "doc_123",
      "text": "OpenShift is a Kubernetes platform...",
      "metadata": {
        "category": "cloud",
        "source": "openshift_docs",
        "language": "en"
      },
      "score": 0.95
    }
  ],
  "metadata": {
    "model": "RedHatAI/granite-3.1-8b-instruct",
    "latency_ms": 1250,
    "query_time_ms": 150,
    "retrieval_time_ms": 200,
    "generation_time_ms": 900
  }
}
```

### More

- For full request/response schemas, error codes, and advanced usage, see [`docs/api.md`](docs/api.md).

## 📋 Prerequisites

- **OpenShift 4.18+** cluster with admin access
- **ElasticSearch 8.x** instance (local or cloud)
- **vLLM server** running with compatible models
- `oc` CLI tool installed and configured
- `podman` or `docker` for container builds
- **Prometheus Operator** (for monitoring)

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
- **Base Image**: Red Hat UBI 9 Python 3.11 (OpenShift 4.18+ optimized)
- **Vector Database**: ElasticSearch 8.x
- **LLM Server**: vLLM with HuggingFace models
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Monitoring**: Prometheus metrics, structured logging, ServiceMonitor
- **Security**: Security Context Constraints (SCC), Network Policies, Pod Security Standards
- **Deployment**: OpenShift 4.18+, Kubernetes 1.28+
- **Testing**: pytest, integration tests, load testing

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pkstaz/rag-openshift-ai-api.git
cd rag-openshift-ai-api
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install testing dependencies
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
ES_URL=https://localhost:9200
ES_INDEX_NAME=rag_documents
ES_USERNAME=elastic
ES_PASSWORD=<your-elasticsearch-password>
ES_TIMEOUT=30
ES_VECTOR_DIMENSION=384

# vLLM Configuration
VLLM_URL=http://localhost:8001
VLLM_MODEL_NAME=RedHatAI/granite-3.1-8b-instruct
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

# Application Configuration
ENV_SECRET_KEY=your-secret-key-change-this-in-deployment
ENV_METRICS_ENABLED=true
```

## 🚀 Deployment

### Automated Deployment Scripts

This project includes several automation scripts for easy deployment:

```bash
# Complete deployment pipeline
./scripts/quick-deploy.sh

# OpenShift Build Script (handles command separation automatically)
./scripts/openshift-build.sh -f Containerfile

# Docker Build Script (supports multiple engines and platforms)
./scripts/build-docker.sh --platform linux/amd64

# Helm Installation Script (automated Helm deployment)
./scripts/helm-install.sh
```

### Option 1: Helm Installation (Recommended)

Helm provides the easiest and most flexible way to deploy the RAG API on OpenShift 4.18+.

#### Prerequisites

```bash
# Install Helm 3.x
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Verify Helm installation
helm version
```

#### Quick Installation

**Using the installation script (Recommended)**

```bash
# Install with default settings
./scripts/helm-install.sh

# Install with custom namespace and release name
./scripts/helm-install.sh -n rag-prod -r rag-api-prod

# Dry run to see what would be installed
./scripts/helm-install.sh -d
```

**Manual Helm installation**

```bash
# 1. Create namespace
oc new-project rag-openshift-ai

# 2. Install with default values
helm install rag-api ./helm \
  --namespace rag-openshift-ai \
  --create-namespace

# 3. Verify installation
helm list -n rag-openshift-ai
oc get all -l app.kubernetes.io/name=rag-api
```

#### Custom Installation

```bash
# 1. Create namespace
oc new-project rag-openshift-ai

# 2. Create custom values file
cat > custom-values.yaml <<EOF
# Image configuration
image:
  repository: your-registry.com/rag-api
  tag: "latest"
  pullPolicy: "Always"

# Elasticsearch configuration
elasticsearch:
  url: "https://your-elasticsearch:9200"
  username: "elastic"
  password: "<your-elasticsearch-password>"

# vLLM configuration
vllm:
  endpoint: "http://your-vllm-service:8000"
  defaultModel: "RedHatAI/granite-3.1-8b-instruct"

# Resource configuration
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"

# Application configuration
app:
  replicas: 3

# Monitoring configuration
monitoring:
  serviceMonitor:
    enabled: true
  prometheusRule:
    enabled: true
EOF

# 3. Install with custom values
helm install rag-api ./helm \
  --namespace rag-openshift-ai \
  --create-namespace \
  --values custom-values.yaml

# 4. Verify installation
helm status rag-api -n rag-openshift-ai
```

### Option 2: OpenShift Native Deployment

#### Prerequisites

```bash
# Install OpenShift CLI
# Download from: https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/

# Login to OpenShift
oc login --token=<your-openshift-token> --server=<your-openshift-server>
```

#### Quick Deployment

```bash
# Deploy everything at once (recommended)
oc apply -f openshift/deployment.yaml
```

#### Manual Deployment

```bash
# 1. Create OpenShift Project
oc new-project rag-openshift-ai

# 2. Build Container Image

# Option A: Using automated script (recommended)
./scripts/openshift-build.sh -f Containerfile

# Option B: Manual build commands
# Step 1: Create build configuration
oc new-build --strategy=docker --binary --name=rag-api --dockerfile=Containerfile

# Step 2: Start the build
oc start-build rag-api --from-dir=. --follow

# 3. Deploy Application
oc apply -f openshift/deployment.yaml

# 4. Verify Deployment
oc get deployment rag-api
oc get pods -l app=rag-api
oc get service rag-api
oc get route rag-api
```

### Option 3: Docker/Podman Build

```bash
# Build image locally
./scripts/build-docker.sh --platform linux/amd64

# Build and push to registry
./scripts/build-docker.sh --registry your-registry.com --push
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
# Health check
curl https://rag-api-rag-openshift-ai.apps.your-cluster.com/health

# Query with authentication (if enabled)
curl -X POST https://rag-api-rag-openshift-ai.apps.your-cluster.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'

# Get metrics
curl https://rag-api-rag-openshift-ai.apps.your-cluster.com/api/v1/metrics
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready

# API info
curl http://localhost:8000/api/v1/info
```

### Prometheus Metrics

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Specific metrics
curl http://localhost:8000/api/v1/metrics | grep rag_api_requests_total
curl http://localhost:8000/api/v1/metrics | grep rag_api_request_duration_seconds
```

### Grafana Dashboard

Access the pre-configured Grafana dashboard:

```bash
# Get Grafana route
oc get route grafana -n openshift-monitoring

# Or access via OpenShift console
# Navigate to: Monitoring > Dashboards > RAG API Dashboard
```

### Structured Logging

```bash
# View application logs with structured format
oc logs -l app=rag-api --tail=100 --timestamps

# Follow logs in real-time
oc logs -l app=rag-api -f --timestamps

# Filter logs by level
oc logs -l app=rag-api --tail=100 | jq 'select(.level == "ERROR")'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_HOST` | API host binding | `0.0.0.0` | No |
| `API_PORT` | API port | `8000` | No |
| `API_DEBUG` | Debug mode | `false` | No |
| `ES_URL` | ElasticSearch URL | - | Yes |
| `ES_USERNAME` | ElasticSearch username | - | No |
| `ES_PASSWORD` | ElasticSearch password | - | No |
| `VLLM_URL` | vLLM server URL | - | Yes |
| `VLLM_MODEL_NAME` | vLLM model name | `RedHatAI/granite-3.1-8b-instruct` | No |
| `EMBEDDING_MODEL_NAME` | Embedding model name | `all-MiniLM-L6-v2` | No |
| `RAG_TOP_K` | Number of documents to retrieve | `5` | No |
| `RAG_SIMILARITY_THRESHOLD` | Minimum similarity score | `0.7` | No |

### Resource Requirements

#### Minimum Requirements
- CPU: 500m (request), 2000m (limit)
- Memory: 1Gi (request), 4Gi (limit)
- Storage: 1Gi for models

#### Recommended Requirements
- CPU: 1000m (request), 4000m (limit)
- Memory: 2Gi (request), 8Gi (limit)
- Storage: 2Gi for models

## 🔒 Security

### Security Context

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
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: allowed-namespace
      ports:
        - protocol: TCP
          port: 8000
```

## 📚 API Documentation

For detailed API documentation, see [docs/api.md](docs/api.md).

### Quick API Examples

```bash
# Health check
curl https://rag-api-rag-openshift-ai.apps.your-cluster.com/health

# Query with authentication (if enabled)
curl -X POST https://rag-api-rag-openshift-ai.apps.your-cluster.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'

# Get metrics
curl https://rag-api-rag-openshift-ai.apps.your-cluster.com/api/v1/metrics
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Pod Startup Failures

```bash
# Check pod status
oc get pods -l app=rag-api

# Check pod events
oc describe pod <pod-name>

# Check logs
oc logs <pod-name>
```

#### 2. Build Failures with OpenShift

```bash
# If you get "no such file or directory" error for Containerfile:
# This project uses Containerfile for building

# Option 1: Using Containerfile (recommended)
oc new-build --strategy=docker --binary --name=rag-api --dockerfile=Containerfile

# If you get "unknown flag: --from-dir" error:
# Make sure to execute commands separately, not together

# Step 1: Create build configuration
oc new-build --strategy=docker --binary --name=rag-api

# Step 2: Start the build (separate command)
oc start-build rag-api --from-dir=. --follow

# Alternative: Use the automated script (recommended)
./scripts/openshift-build.sh -f Containerfile

# Check build logs
oc logs build/rag-api-1

# Check build status
oc get builds
```

#### 3. Service Unavailable

```bash
# Check service endpoints
oc get endpoints rag-api

# Test service connectivity
oc exec <pod-name> -- curl http://rag-api:8000/health

# Check route
oc get route rag-api -o yaml
```

#### 4. High Resource Usage

```bash
# Check resource usage
oc top pods -l app=rag-api

# Check resource limits
oc describe pod <pod-name> | grep -A 10 "Limits:"
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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

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
- **Issues**: [GitHub Issues](https://github.com/pkstaz/rag-openshift-ai-api/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pkstaz/rag-openshift-ai-api/discussions)

## 📚 Additional Documentation

- [Helm Installation Guide](docs/HELM_INSTALLATION.md) - Complete Helm deployment guide
- [API Documentation](docs/api.md) - Detailed API reference and examples
- [OpenShift Deployment](docs/OPENSHIFT.md) - Manual OpenShift deployment instructions
- [API Testing](docs/API_TESTING.md) - Testing strategies and examples

## 🔗 Related Projects

- [ElasticSearch](https://www.elastic.co/elasticsearch/)
- [vLLM](https://github.com/vllm-project/vllm)
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift)
- [Red Hat UBI](https://developers.redhat.com/products/ubi/overview)
- [Prometheus Operator](https://prometheus-operator.dev/)

---

**Author**: Carlos Estay  
**GitHub**: [pkstaz](https://github.com/pkstaz)  
**Email**: c.estay.g@gmail.com