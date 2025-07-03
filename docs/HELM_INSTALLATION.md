# Helm Installation Guide

## Overview

This guide provides detailed instructions for installing and managing the RAG OpenShift AI API using Helm on OpenShift 4.18+.

## Prerequisites

### Required Tools

```bash
# Install Helm 3.x
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Verify installation
helm version

# Install OpenShift CLI
# Download from: https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/
```

### Required Services

- **OpenShift 4.18+** cluster with admin access
- **Elasticsearch 8.x** instance (with HTTPS enabled)
- **vLLM server** running with RedHatAI/granite-3.1-8b-instruct model
- **Prometheus Operator** (for monitoring)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/rag-openshift-ai-api.git
cd rag-openshift-ai-api
```

### 2. Create Namespace

```bash
oc new-project rag-demo
```

### 3. Install with Default Values

```bash
helm install rag-api ./helm \
  --namespace rag-demo \
  --create-namespace
```

### 4. Verify Installation

```bash
# Check Helm release
helm list -n rag-demo

# Check resources
oc get all -l app.kubernetes.io/name=rag-api

# Check pods
oc get pods -l app.kubernetes.io/name=rag-api

# Check routes
oc get routes -l app.kubernetes.io/name=rag-api
```

## Configuration Options

### Basic Configuration

Create a custom values file:

```yaml
# custom-values.yaml
image:
  repository: your-registry.com/rag-api
  tag: "latest"
  pullPolicy: "Always"

replicaCount: 2

config:
  elasticsearch:
    url: "https://your-elasticsearch:9200"
    index: "rag-documents"
    username: "elastic"
    password: "your-password"
  
  vllm:
    endpoint: "http://your-vllm-service:8000"
    defaultModel: "RedHatAI/granite-3.1-8b-instruct"
    maxTokens: 2048
    temperature: 0.7

resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

### Advanced Configuration

```yaml
# advanced-values.yaml
image:
  repository: your-registry.com/rag-api
  tag: "latest"
  pullPolicy: "Always"
  pullSecrets:
    - name: your-registry-secret

replicaCount: 3

# API Configuration
config:
  api:
    logLevel: "INFO"
    debug: false
    corsOrigins: ["https://your-frontend.com"]
    maxRequestSize: "10MB"
    requestTimeout: 300
    rateLimit:
      enabled: true
      requestsPerMinute: 60
      burstSize: 10

# Elasticsearch Configuration
config:
  elasticsearch:
    url: "https://elasticsearch-cluster:9200"
    index: "rag-documents"
    username: "elastic"
    password: "your-secure-password"
    sslVerify: true
    timeout: 30
    maxRetries: 3
    maxConnections: 20
    retryOnTimeout: true

# vLLM Configuration
config:
  vllm:
    endpoint: "http://vllm-service:8000"
    defaultModel: "RedHatAI/granite-3.1-8b-instruct"
    maxTokens: 2048
    temperature: 0.7
    topP: 0.9
    timeout: 60

# RAG Configuration
config:
  rag:
    retrieval:
      topK: 5
      similarityThreshold: 0.7
      maxTokens: 4000
      searchType: "hybrid"
    generation:
      maxTokens: 2048
      temperature: 0.7
      topP: 0.9
      topK: 50
      repetitionPenalty: 1.1
    cache:
      enabled: true
      ttl: 3600
      maxSize: 1000

# Resource Management
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"

# Security Configuration
security:
  podSecurityStandards:
    enabled: true
    level: "restricted"
    version: "v1.24"
    audit: "restricted"
    warn: "restricted"
    enforce: "restricted"

# Monitoring Configuration
monitoring:
  serviceMonitor:
    enabled: true
    interval: "30s"
    scrapeTimeout: "10s"
    path: "/api/v1/metrics"
    port: "http"
    honorLabels: true
  prometheusRule:
    enabled: true
    name: "rag-api-alerts"
    rules:
      - alert: RAGAPIHighErrorRate
        expr: rate(rag_api_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in RAG API"
          description: "RAG API is experiencing high error rate"

# OpenShift Specific
openshift:
  scc:
    enabled: true
    name: "rag-api-scc"
    priority: 10
  route:
    enabled: true
    host: "rag-api-rag-demo.apps.your-cluster.com"
    tls:
      enabled: true
      termination: edge
      insecureEdgeTerminationPolicy: Redirect
    annotations:
      haproxy.router.openshift.io/timeout: 300s
      haproxy.router.openshift.io/rate-limit-connections: "true"

# Network Policy
networkPolicy:
  enabled: true
  ingressRules:
    - from:
        - namespaceSelector:
            matchLabels:
              name: allowed-namespace
      ports:
        - protocol: TCP
          port: 8000
  egressRules:
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
          port: 8000

# Horizontal Pod Autoscaler
hpa:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
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

# Pod Disruption Budget
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

## Installation Commands

### Basic Installation

```bash
helm install rag-api ./helm \
  --namespace rag-demo \
  --create-namespace
```

### Installation with Custom Values

```bash
helm install rag-api ./helm \
  --namespace rag-demo \
  --create-namespace \
  --values custom-values.yaml
```

### Installation with Command Line Overrides

```bash
helm install rag-api ./helm \
  --namespace rag-demo \
  --create-namespace \
  --set image.repository=your-registry.com/rag-api \
  --set image.tag=latest \
  --set replicaCount=3 \
  --set config.elasticsearch.url=https://your-elasticsearch:9200 \
  --set config.vllm.endpoint=http://your-vllm-service:8000 \
  --set monitoring.serviceMonitor.enabled=true \
  --set security.podSecurityStandards.level=restricted
```

### Installation with Secrets

```bash
# Create secret for registry
oc create secret docker-registry your-registry-secret \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password

# Install with registry secret
helm install rag-api ./helm \
  --namespace rag-demo \
  --create-namespace \
  --set image.pullSecrets[0].name=your-registry-secret
```

## Management Operations

### Upgrade Deployment

```bash
# Upgrade with new values
helm upgrade rag-api ./helm \
  --namespace rag-demo \
  --values custom-values.yaml

# Upgrade with specific overrides
helm upgrade rag-api ./helm \
  --namespace rag-demo \
  --set image.tag=new-version \
  --set replicaCount=4
```

### Rollback Deployment

```bash
# List revisions
helm history rag-api -n rag-demo

# Rollback to previous version
helm rollback rag-api -n rag-demo

# Rollback to specific revision
helm rollback rag-api 2 -n rag-demo
```

### Uninstall Deployment

```bash
# Uninstall with cleanup
helm uninstall rag-api -n rag-demo

# Uninstall and keep resources
helm uninstall rag-api -n rag-demo --keep-history
```

### Get Information

```bash
# Get release status
helm status rag-api -n rag-demo

# Get values
helm get values rag-api -n rag-demo

# Get manifest
helm get manifest rag-api -n rag-demo

# Get hooks
helm get hooks rag-api -n rag-demo

# Get notes
helm get notes rag-api -n rag-demo
```

## Troubleshooting

### Common Issues

#### 1. Pod Not Starting

```bash
# Check pod status
oc get pods -l app.kubernetes.io/name=rag-api -n rag-demo

# Check pod events
oc describe pod <pod-name> -n rag-demo

# Check logs
oc logs <pod-name> -n rag-demo

# Check Helm release status
helm status rag-api -n rag-demo
```

#### 2. Image Pull Issues

```bash
# Check image pull secret
oc get secret your-registry-secret -n rag-demo

# Test image pull
oc run test-pod --image=your-registry.com/rag-api:latest --rm -it

# Check events
oc get events --sort-by='.lastTimestamp' -n rag-demo | grep -i image
```

#### 3. Configuration Issues

```bash
# Validate Helm chart
helm lint ./helm

# Dry run installation
helm install rag-api ./helm \
  --namespace rag-demo \
  --dry-run \
  --values custom-values.yaml

# Check ConfigMap
oc get configmap rag-api-config -n rag-demo -o yaml

# Check Secret
oc get secret rag-api-secret -n rag-demo -o yaml
```

#### 4. Network Issues

```bash
# Check Network Policies
oc get networkpolicy -n rag-demo

# Test connectivity
oc exec <pod-name> -n rag-demo -- curl https://elasticsearch:9200/_cluster/health

# Check routes
oc get routes -n rag-demo
```

#### 5. Monitoring Issues

```bash
# Check Service Monitor
oc get servicemonitor rag-api-monitor -n rag-demo

# Check Prometheus Rules
oc get prometheusrule rag-api-alerts -n rag-demo

# Check metrics endpoint
oc exec <pod-name> -n rag-demo -- curl http://localhost:8000/api/v1/metrics
```

### Debug Commands

```bash
# Enable debug logging
helm upgrade rag-api ./helm \
  --namespace rag-demo \
  --set config.api.debug=true \
  --set config.api.logLevel=DEBUG

# Check all resources
oc get all -l app.kubernetes.io/name=rag-api -n rag-demo

# Check events
oc get events --sort-by='.lastTimestamp' -n rag-demo | grep rag-api

# Check resource usage
oc top pods -l app.kubernetes.io/name=rag-api -n rag-demo

# Check HPA status
oc get hpa rag-api-hpa -n rag-demo
```

## Best Practices

### 1. Resource Management

- Set appropriate resource requests and limits
- Use Horizontal Pod Autoscaler for scaling
- Monitor resource usage regularly

### 2. Security

- Use Pod Security Standards (restricted level)
- Enable Security Context Constraints
- Use Network Policies for network isolation
- Store secrets in Kubernetes Secrets

### 3. Monitoring

- Enable Service Monitor for Prometheus integration
- Configure Prometheus Rules for alerting
- Use structured logging
- Monitor application metrics

### 4. Backup and Recovery

- Use Helm hooks for backup operations
- Implement proper rollback strategies
- Document configuration changes

### 5. Updates and Maintenance

- Use semantic versioning for images
- Test upgrades in staging environment
- Use Helm rollback for quick recovery
- Monitor deployment health after updates

## Examples

### Production Deployment

```bash
# Create production namespace
oc new-project rag-production

# Create production values
cat > production-values.yaml <<EOF
image:
  repository: your-registry.com/rag-api
  tag: "v1.0.0"
  pullPolicy: "Always"

replicaCount: 3

config:
  elasticsearch:
    url: "https://elasticsearch-prod:9200"
    username: "elastic"
    password: "prod-password"
  
  vllm:
    endpoint: "http://vllm-prod:8000"
    defaultModel: "RedHatAI/granite-3.1-8b-instruct"

resources:
  requests:
    cpu: "1000m"
    memory: "2Gi"
  limits:
    cpu: "4000m"
    memory: "8Gi"

monitoring:
  serviceMonitor:
    enabled: true
  prometheusRule:
    enabled: true

security:
  podSecurityStandards:
    level: "restricted"
EOF

# Install production deployment
helm install rag-api-prod ./helm \
  --namespace rag-production \
  --values production-values.yaml
```

### Development Deployment

```bash
# Create development namespace
oc new-project rag-development

# Install with development settings
helm install rag-api-dev ./helm \
  --namespace rag-development \
  --set replicaCount=1 \
  --set config.api.debug=true \
  --set config.api.logLevel=DEBUG \
  --set resources.requests.cpu=250m \
  --set resources.requests.memory=512Mi \
  --set resources.limits.cpu=1000m \
  --set resources.limits.memory=2Gi
```

## Support

For additional support:

- Check the [main README](../README.md)
- Review [API documentation](api.md)
- Open an issue on GitHub
- Contact the development team 