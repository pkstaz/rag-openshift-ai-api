# OpenShift 4.18+ Compatibility Guide

## Overview

This document outlines the specific optimizations and features implemented for OpenShift 4.18+ compatibility, ensuring enterprise-grade security, monitoring, and performance.

## 🚀 Key Enhancements

### 1. Base Image Optimization

**Red Hat UBI 9 Python 3.11**
- Enterprise-grade base image
- Security patches and updates
- OpenShift-native compatibility
- Optimized for container performance

```dockerfile
FROM registry.access.redhat.com/ubi9/python-311:1-209 as base
```

### 2. Security Context Constraints (SCC)

Custom SCC for maximum security compliance:

```yaml
apiVersion: security.openshift.io/v1
kind: SecurityContextConstraints
metadata:
  name: rag-api-scc
spec:
  allowHostDirVolumePlugin: false
  allowHostIPC: false
  allowHostNetwork: false
  allowHostPID: false
  allowHostPorts: false
  allowPrivilegeEscalation: false
  allowPrivilegedContainer: false
  allowedCapabilities: []
  fsGroup:
    type: MustRunAs
    ranges:
      - min: 1001
        max: 1001
  runAsUser:
    type: MustRunAs
    uid: 1001
  seccompProfiles:
    - RuntimeDefault
```

### 3. Pod Security Standards

Compliant with Kubernetes Pod Security Standards v1.24+:

- **Level**: Restricted (highest security)
- **Enforcement**: Audit, Warn, and Enforce modes
- **Runtime Security**: Seccomp and AppArmor profiles

### 4. Advanced Network Policies

Granular network control with namespace isolation:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
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
```

## 📊 Monitoring & Observability

### 1. Service Monitor Integration

Automatic Prometheus integration:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: rag-api-monitor
spec:
  selector:
    matchLabels:
      app: rag-api
  endpoints:
  - port: http
    path: /api/v1/metrics
    interval: 30s
    scrapeTimeout: 10s
```

### 2. Prometheus Alerting Rules

Pre-configured alerts for production monitoring:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
  - name: rag-api.rules
    rules:
    - alert: RAGAPIHighErrorRate
      expr: rate(rag_api_errors_total[5m]) > 0.1
      for: 2m
      labels:
        severity: warning
    - alert: RAGAPIHighLatency
      expr: histogram_quantile(0.95, rate(rag_api_request_duration_seconds_bucket[5m])) > 5
      for: 2m
      labels:
        severity: warning
```

### 3. Structured Logging

JSON-formatted logs with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "correlation_id": "req-12345",
  "service": "rag-api",
  "message": "Processing RAG query",
  "query": "What is OpenShift?",
  "duration_ms": 1500
}
```

## 🔧 Deployment

### Complete Deployment (Recommended)

Deploy everything with a single command:

```bash
# Create project
oc new-project rag-demo

# Apply complete configuration
oc apply -f openshift/deployment.yaml

# Verify deployment
oc get all -l app=rag-api
```

### Alternative: OpenShift Build Strategy

Use OpenShift's native build capabilities:

```bash
# Create build configuration
oc new-build --strategy=docker --binary --name=rag-api

# Start build from local directory
oc start-build rag-api --from-dir=. --follow

# Deploy application
oc rollout status deployment/rag-api
```

## 🔒 Security Features

### 1. Non-Root Execution

All containers run as non-root user (UID 1001):

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  fsGroup: 1001
```

### 2. Read-Only Root Filesystem

Enhanced security with read-only root:

```yaml
securityContext:
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### 3. Seccomp Profiles

Container isolation with RuntimeDefault profile:

```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

## 📈 Performance Optimizations

### 1. Resource Management

Optimized resource requests and limits:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### 2. Horizontal Pod Autoscaler

Automatic scaling based on metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
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
```

### 3. Pod Disruption Budget

High availability during updates:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: rag-api
```

## 🏢 Enterprise Features

### 1. Resource Quotas

Resource management and limits:

```yaml
apiVersion: v1
kind: ResourceQuota
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    pods: "10"
```

### 2. Limit Ranges

Default resource constraints:

```yaml
apiVersion: v1
kind: LimitRange
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "1Gi"
    defaultRequest:
      cpu: "250m"
      memory: "512Mi"
    max:
      cpu: "2000m"
      memory: "4Gi"
```

### 3. Affinity Rules

Pod distribution across nodes:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - rag-api
        topologyKey: kubernetes.io/hostname
```

## 🔍 Troubleshooting

### 1. Security Context Issues

```bash
# Check SCC status
oc get scc rag-api-scc

# Verify pod security
oc describe pod <pod-name> | grep -A 10 "Security Context"

# Check security events
oc get events --sort-by='.lastTimestamp' | grep -i security
```

### 2. Monitoring Issues

```bash
# Check Service Monitor
oc get servicemonitor rag-api-monitor -o yaml

# Verify Prometheus targets
oc get route prometheus-k8s -n openshift-monitoring

# Check metrics endpoint
curl http://rag-api:8000/api/v1/metrics
```

### 3. Network Policy Issues

```bash
# Check Network Policies
oc get networkpolicy rag-api-network-policy -o yaml

# Test connectivity
oc exec <pod-name> -- curl http://elasticsearch:9200/_cluster/health

# Check network events
oc get events --sort-by='.lastTimestamp' | grep -i network
```

## 📋 Compliance Checklist

### Security Compliance

- [ ] Security Context Constraints configured
- [ ] Pod Security Standards enforced
- [ ] Network Policies implemented
- [ ] Non-root execution enabled
- [ ] Read-only root filesystem
- [ ] Seccomp profiles configured
- [ ] Capability restrictions applied

### Monitoring Compliance

- [ ] Service Monitor configured
- [ ] Prometheus Rules defined
- [ ] Alerting rules active
- [ ] Metrics endpoint accessible
- [ ] Logging structured and centralized
- [ ] Performance monitoring enabled

### Operational Compliance

- [ ] Resource quotas defined
- [ ] Limit ranges configured
- [ ] HPA configured and working
- [ ] PDB configured for HA
- [ ] Affinity rules applied
- [ ] Health checks configured

## 🔗 Additional Resources

- [OpenShift 4.18 Documentation](https://docs.openshift.com/container-platform/4.18/)
- [Security Context Constraints](https://docs.openshift.com/container-platform/4.18/authentication/managing-security-context-constraints.html)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Red Hat UBI](https://developers.redhat.com/products/ubi/overview) 