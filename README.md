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

- **OpenShift 4.18+** cluster with admin access
- **ElasticSearch 8.x** instance (local or cloud)
- **vLLM server** running with compatible models
- `oc` CLI tool installed and configured
- `podman` or `docker` for container builds
- **Prometheus Operator** (for monitoring)
- **OpenShift Service Mesh** (optional, for advanced networking)

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
- **Observability**: Prometheus, Grafana, AlertManager

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
ES_URL=https://localhost:9200
ES_INDEX_NAME=rag_documents
ES_USERNAME=elastic
ES_PASSWORD=your-password
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

# Environment Configuration
ENV_ENVIRONMENT=production
ENV_METRICS_ENABLED=true
ENV_SECRET_KEY=your-secret-key-change-in-production
```

## 🚀 Deployment Options

### Option 1: Helm Installation (Recommended)

Helm provides the easiest and most flexible way to deploy the RAG API on OpenShift 4.18+.

#### Prerequisites

```bash
# Install Helm 3.x
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Verify Helm installation
helm version

# Add required repositories (if needed)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

#### Quick Installation

**Option A: Using the installation script (Recommended)**

```bash
# Install development deployment
./scripts/helm-install.sh -t development

# Install production deployment
./scripts/helm-install.sh -t production -n rag-prod

# Install with custom namespace and release name
./scripts/helm-install.sh -t production -n rag-prod -r rag-api-prod

# Dry run to see what would be installed
./scripts/helm-install.sh -t production -d
```

**Option B: Manual Helm installation**

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
config:
  elasticsearch:
    url: "https://your-elasticsearch:9200"
    username: "elastic"
    password: "your-password"

# vLLM configuration
config:
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

# Replica configuration
replicaCount: 3

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

#### Advanced Configuration

```bash
# Install with specific configurations
helm install rag-api ./helm \
  --namespace rag-openshift-ai \
  --create-namespace \
  --set image.repository=your-registry.com/rag-api \
  --set image.tag=latest \
  --set replicaCount=3 \
  --set config.elasticsearch.url=https://your-elasticsearch:9200 \
  --set config.vllm.endpoint=http://your-vllm-service:8000 \
  --set monitoring.serviceMonitor.enabled=true \
  --set monitoring.prometheusRule.enabled=true \
  --set security.podSecurityStandards.level=restricted \
  --set openshift.scc.enabled=true
```

#### Helm Values Configuration

The Helm chart supports extensive customization through values. See `helm/values.yaml` for complete configuration options.

**Quick Examples:**

```yaml
# Basic configuration
image:
  repository: rag-openshift-ai-api
  tag: "latest"

config:
  elasticsearch:
    url: "https://elasticsearch:9200"
    username: "elastic"
    password: "your-password"
  
  vllm:
    endpoint: "http://vllm-service:8000"
    defaultModel: "RedHatAI/granite-3.1-8b-instruct"

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

**Pre-configured Examples:**

The project includes pre-configured examples for different deployment scenarios:

- **Development**: `helm/values-examples.yaml#development`
- **Production**: `helm/values-examples.yaml#production`
- **High Availability**: `helm/values-examples.yaml#high-availability`
- **Multi-Tenant**: `helm/values-examples.yaml#multi-tenant`
- **Edge/Remote**: `helm/values-examples.yaml#edge`
- **Testing/CI**: `helm/values-examples.yaml#testing`

**Usage:**
```bash
# Install with production configuration
helm install rag-api ./helm \
  --namespace rag-prod \
  --values helm/values-examples.yaml \
  --set-string config=production

# Install with development configuration
helm install rag-api-dev ./helm \
  --namespace rag-dev \
  --values helm/values-examples.yaml \
  --set-string config=development
```

#### Helm Operations

```bash
# Upgrade deployment
helm upgrade rag-api ./helm \
  --namespace rag-openshift-ai \
  --values custom-values.yaml

# Rollback to previous version
helm rollback rag-api -n rag-openshift-ai

# Uninstall deployment
helm uninstall rag-api -n rag-openshift-ai

# Get deployment status
helm status rag-api -n rag-openshift-ai

# List all releases
helm list -n rag-openshift-ai

# Get values
helm get values rag-api -n rag-openshift-ai

# Get manifest
helm get manifest rag-api -n rag-openshift-ai
```

#### Troubleshooting Helm Installation

```bash
# Check Helm release status
helm status rag-api -n rag-openshift-ai

# Check pod status
oc get pods -l app.kubernetes.io/name=rag-api -n rag-openshift-ai

# Check events
oc get events --sort-by='.lastTimestamp' -n rag-openshift-ai | grep rag-api

# Check logs
oc logs -l app.kubernetes.io/name=rag-api -n rag-openshift-ai --tail=50

# Check Helm hooks
helm get hooks rag-api -n rag-openshift-ai

# Validate Helm chart
helm lint ./helm
```

### Option 2: Manual Deployment

#### 1. Build Container Image (OpenShift 4.18+ Optimized)

```bash
# Build the container image with OpenShift 4.18+ optimizations
podman build --platform linux/amd64 -t rag-api:latest .

# Tag for your registry (replace with your registry)
podman tag rag-api:latest your-registry.com/rag-api:latest

# Push to registry
podman push your-registry.com/rag-api:latest

# Alternative: Build directly in OpenShift
oc new-build --strategy=docker --binary --name=rag-api
oc start-build rag-api --from-dir=. --follow
```

### 2. Create OpenShift Project

```bash
# Create new project
oc new-project rag-openshift-ai

# Or use existing project
oc project rag-openshift-ai
```

#### 3. Deploy Complete Application

```bash
# Deploy everything at once (recommended)
oc apply -f openshift/deployment.yaml

# Or deploy step by step if needed
oc create serviceaccount rag-api-sa
oc apply -f openshift/deployment.yaml
```

#### 4. Verify Deployment (OpenShift 4.18+)

```bash
# Check deployment status
oc get deployment rag-api

# Check pods with detailed information
oc get pods -l app=rag-api -o wide

# Check service
oc get service rag-api

# Check route
oc get route rag-api

# Check Security Context Constraints
oc get scc rag-api-scc

# Check Network Policies
oc get networkpolicy rag-api-network-policy

# Check Service Monitor
oc get servicemonitor rag-api-monitor

# Check Prometheus Rules
oc get prometheusrule rag-api-alerts

# Check logs with structured format
oc logs -l app=rag-api --tail=50 --timestamps

# Check resource usage
oc top pods -l app=rag-api

# Check events
oc get events --sort-by='.lastTimestamp' | grep rag-api
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

## 📊 Monitoring & Observability (OpenShift 4.18+)

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready

# API info
curl http://localhost:8000/api/v1/info

# Detailed health with OpenShift headers
curl -H "User-Agent: OpenShift-Health-Check" http://localhost:8000/health
```

### Prometheus Metrics

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Specific metrics
curl http://localhost:8000/api/v1/metrics | grep rag_api_requests_total
curl http://localhost:8000/api/v1/metrics | grep rag_api_request_duration_seconds

# Service Monitor verification
oc get servicemonitor rag-api-monitor -o yaml
```

### Grafana Dashboard

Access the pre-configured Grafana dashboard:

```bash
# Get Grafana route
oc get route grafana -n openshift-monitoring

# Or access via OpenShift console
# Navigate to: Monitoring > Dashboards > RAG API Dashboard
```

### Alerting

Monitor alerts in OpenShift:

```bash
# Check Prometheus rules
oc get prometheusrule rag-api-alerts -o yaml

# View alerts in Prometheus
oc get route prometheus-k8s -n openshift-monitoring

# Check AlertManager
oc get route alertmanager-main -n openshift-monitoring
```

### Structured Logging

```bash
# View application logs with structured format
oc logs -l app=rag-api --tail=100 --timestamps

# Follow logs in real-time
oc logs -l app=rag-api -f --timestamps

# Filter logs by level
oc logs -l app=rag-api --tail=100 | jq 'select(.level == "ERROR")'

# Logs with correlation IDs
oc logs -l app=rag-api --tail=100 | jq '.correlation_id'
```

### Performance Monitoring

```bash
# Resource usage
oc top pods -l app=rag-api

# Pod metrics
oc adm top pods --containers -l app=rag-api

# Node resource usage
oc adm top nodes

# HPA status
oc get hpa rag-api-hpa -o yaml
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Host to bind the server | `0.0.0.0` |
| `API_PORT` | Port to bind the server | `8000` |
| `API_DEBUG` | Debug mode | `false` |
| `ES_URL` | ElasticSearch URL | `https://localhost:9200` |
| `ES_INDEX_NAME` | Index name for documents | `rag_documents` |
| `VLLM_URL` | vLLM server URL | `http://localhost:8001` |
| `VLLM_MODEL_NAME` | Default model name | `RedHatAI/granite-3.1-8b-instruct` |
| `EMBEDDING_MODEL_NAME` | Embedding model name | `sentence-transformers/all-MiniLM-L6-v2` |
| `RAG_TOP_K` | Number of documents to retrieve | `5` |

### Resource Requirements

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| RAG API | 250m | 500m | 512Mi | 1Gi |
| ElasticSearch | 500m | 1000m | 1Gi | 2Gi |
| vLLM Server | 1000m | 2000m | 2Gi | 4Gi |

## 🔒 Security (OpenShift 4.18+)

### Security Context Constraints (SCC)

The deployment includes custom SCC for enhanced security:

- **Non-root execution**: UID/GID 1001
- **Read-only root filesystem**: Prevents file system modifications
- **No privilege escalation**: Enhanced security posture
- **Seccomp profiles**: RuntimeDefault for container isolation
- **Capability restrictions**: All capabilities dropped
- **Volume restrictions**: Only necessary volume types allowed

### Network Policies

Advanced network security with granular control:

- **Ingress**: Only from allowed namespaces and services
- **Egress**: Restricted to ElasticSearch, vLLM, and DNS only
- **Port restrictions**: Specific ports for each service
- **Namespace isolation**: Prevents unauthorized cross-namespace communication

### Pod Security Standards

Compliant with Kubernetes Pod Security Standards:

- **Level**: Restricted (highest security level)
- **Version**: v1.24+ compatible
- **Enforcement**: Audit, Warn, and Enforce modes
- **Runtime security**: Seccomp and AppArmor profiles

### Secrets Management

Enterprise-grade secrets handling:

- **Encryption at rest**: All secrets encrypted
- **RBAC protection**: Role-based access control
- **Audit logging**: All secret access logged
- **Rotation support**: Easy secret rotation process

### Compliance Features

- **SOC 2 Type II** ready configurations
- **GDPR** compliant data handling
- **HIPAA** compatible security measures
- **PCI DSS** security controls

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

## 🚀 OpenShift 4.18+ Specific Features

### Enhanced Security

- **Security Context Constraints (SCC)**: Custom SCC for maximum security
- **Pod Security Standards**: Restricted level compliance
- **Network Policies**: Granular network control
- **Seccomp Profiles**: RuntimeDefault for container isolation
- **Capability Restrictions**: All unnecessary capabilities dropped

### Advanced Monitoring

- **ServiceMonitor**: Automatic Prometheus integration
- **PrometheusRule**: Pre-configured alerts
- **Grafana Dashboard**: Ready-to-use monitoring dashboard
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Performance Metrics**: CPU, memory, and custom metrics

### Enterprise Features

- **Horizontal Pod Autoscaler**: Automatic scaling based on metrics
- **Pod Disruption Budget**: High availability during updates
- **Resource Quotas**: Resource management and limits
- **Limit Ranges**: Default resource constraints
- **Affinity Rules**: Pod distribution across nodes

### Deployment

#### Complete Deployment (Recommended)
```bash
# Deploy everything at once
oc apply -f openshift/deployment.yaml
```

#### Alternative: OpenShift Build Strategy
```bash
# 1. Create namespace and project
oc new-project rag-openshift-ai

# 2. Apply deployment configuration
oc apply -f openshift/deployment.yaml

# 3. Build and deploy using OpenShift build
oc new-build --strategy=docker --binary --name=rag-api
oc start-build rag-api --from-dir=. --follow
oc rollout status deployment/rag-api
```

### OpenShift Console Integration

- **Web Console**: Full integration with OpenShift web interface
- **CLI Tools**: Enhanced `oc` commands for RAG API management
- **Monitoring Stack**: Native Prometheus/Grafana integration
- **Logging**: Centralized logging with OpenShift logging stack
- **Metrics**: Built-in metrics collection and visualization

### Compliance and Governance

- **SOC 2 Type II**: Ready configurations for compliance
- **GDPR**: Data protection and privacy controls
- **HIPAA**: Healthcare data security measures
- **PCI DSS**: Payment card industry security standards
- **Audit Logging**: Comprehensive audit trail

## 📚 Additional Documentation

- [Helm Installation Guide](docs/HELM_INSTALLATION.md) - Complete Helm deployment guide with examples
- [API Documentation](docs/api.md) - Detailed API reference and examples
- [OpenShift Deployment](docs/OPENSHIFT.md) - Manual OpenShift deployment instructions
- [Container Guide](docs/CONTAINER.md) - Container build and optimization guide
- [API Testing](docs/API_TESTING.md) - Testing strategies and examples

## 🔗 Related Projects

- [ElasticSearch](https://www.elastic.co/elasticsearch/)
- [vLLM](https://github.com/vllm-project/vllm)
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift)
- [Red Hat UBI](https://developers.redhat.com/products/ubi/overview)
- [Prometheus Operator](https://prometheus-operator.dev/)
