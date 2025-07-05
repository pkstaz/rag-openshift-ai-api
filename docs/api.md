# RAG OpenShift AI API Documentation

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Request/Response Schemas](#requestresponse-schemas)
- [Usage Examples](#usage-examples)
- [Model Configuration](#model-configuration)
- [Integration Guide](#integration-guide)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)
- [API Reference](#api-reference)

## Overview

### Purpose and Functionality

The RAG OpenShift AI API is a Retrieval-Augmented Generation (RAG) service designed for enterprise environments running on OpenShift. It combines the power of vector search with large language models to provide accurate, contextual responses to user queries.

**Key Features:**
- **Vector Search**: Semantic document retrieval using ElasticSearch
- **Text Generation**: AI-powered response generation using vLLM
- **Metadata Filtering**: Advanced filtering capabilities for precise results
- **Enterprise Ready**: OpenShift-native deployment with security and monitoring
- **Scalable**: Horizontal scaling and load balancing support

### Architecture

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

**Components:**
- **FastAPI Application**: Main API server with async support
- **ElasticSearch**: Vector database for document storage and retrieval
- **vLLM Server**: High-performance LLM inference server
- **Embedding Model**: Sentence transformers for text vectorization
- **Prometheus**: Metrics collection and monitoring

### Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic
- **Vector Database**: ElasticSearch 8.x
- **LLM Server**: vLLM with HuggingFace models
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Monitoring**: Prometheus metrics, structured logging
- **Deployment**: OpenShift, Kubernetes, Helm
- **Testing**: pytest, integration tests, load testing

## Quick Start

### Prerequisites

- Access to OpenShift cluster
- ElasticSearch instance (local or cloud)
- vLLM server running with compatible models
- Network access to API endpoints

### Basic Usage

```bash
# Health check
curl http://localhost:8000/health

# Basic RAG query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'
```

### OpenShift Deployment

```bash
# Deploy to OpenShift
./scripts/helm-install.sh -t production -n rag-demo

# Get route URL
oc get route rag-api -o jsonpath='{.spec.host}'

# Test deployed API
curl https://rag-api-rag-demo.apps.example.com/health
```

## Authentication

### Current Implementation

The API currently operates without authentication, designed for use within private networks or secure OpenShift environments.

**Security Considerations:**
- Deploy within private OpenShift namespaces
- Use NetworkPolicies to restrict access
- Monitor API usage through metrics
- Consider implementing authentication for production use

### Network Access

**Required Access:**
- API endpoint (port 8000)
- ElasticSearch (port 9200)
- vLLM server (port 8001)

**OpenShift NetworkPolicy Example:**
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

## Endpoints

### POST /api/v1/query

Main RAG endpoint for processing queries and generating responses.

**URL:** `POST /api/v1/query`

**Description:** Processes a natural language query, retrieves relevant documents from ElasticSearch, and generates a contextual response using the specified language model.

**Request Body:**
```json
{
  "query": "string (required)",
  "top_k": "integer (optional, default: 5)",
  "filters": "object (optional)",
  "model_name": "string (optional, default: RedHatAI/granite-3.1-8b-instruct)"
}
```

**Response:**
```json
{
  "answer": "string",
  "sources": [
    {
      "id": "string",
      "text": "string",
      "metadata": "object",
      "score": "float"
    }
  ],
  "metadata": {
    "model": "string",
    "latency_ms": "integer",
    "query_time_ms": "integer",
    "retrieval_time_ms": "integer",
    "generation_time_ms": "integer"
  }
}
```

### GET /health

Basic health check endpoint.

**URL:** `GET /health`

**Description:** Returns the basic health status of the API service.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T14:30:25Z",
  "version": "0.1.0"
}
```

### GET /ready

Readiness check endpoint.

**URL:** `GET /ready`

**Description:** Checks if the API and all dependencies are ready to serve requests.

**Response (Ready):**
```json
{
  "status": "ready",
  "dependencies": {
    "elasticsearch": "ok",
    "vLLM": "ok",
    "embeddings": "ok"
  },
  "timestamp": "2024-01-15T14:30:25Z"
}
```

**Response (Not Ready):**
```json
{
  "status": "unavailable",
  "dependencies": {
    "elasticsearch": "error",
    "vLLM": "ok",
    "embeddings": "ok"
  },
  "errors": ["ElasticSearch connection failed"],
  "timestamp": "2024-01-15T14:30:25Z"
}
```

### GET /api/v1/metrics

Prometheus metrics endpoint.

**URL:** `GET /api/v1/metrics`

**Description:** Returns Prometheus-formatted metrics for monitoring and alerting.

**Response:**
```text
# HELP rag_api_requests_total Total number of API requests
# TYPE rag_api_requests_total counter
rag_api_requests_total{endpoint="/api/v1/query",method="POST",status="200"} 150

# HELP rag_api_request_duration_seconds Request duration in seconds
# TYPE rag_api_request_duration_seconds histogram
rag_api_request_duration_seconds_bucket{endpoint="/api/v1/query",le="0.1"} 10
rag_api_request_duration_seconds_bucket{endpoint="/api/v1/query",le="0.5"} 45
rag_api_request_duration_seconds_bucket{endpoint="/api/v1/query",le="1.0"} 120
rag_api_request_duration_seconds_bucket{endpoint="/api/v1/query",le="+Inf"} 150

# HELP rag_retrieval_documents_total Total number of documents retrieved
# TYPE rag_retrieval_documents_total counter
rag_retrieval_documents_total 750

# HELP rag_generation_tokens_total Total number of tokens generated
# TYPE rag_generation_tokens_total counter
rag_generation_tokens_total 15000
```

### GET /api/v1/info

API information endpoint.

**URL:** `GET /api/v1/info`

**Description:** Returns information about the API, including version, configuration, and available models.

**Response:**
```json
{
  "title": "RAG OpenShift AI API",
  "version": "0.1.0",
  "description": "RAG agent for OpenShift AI",
  "environment": "production",
  "models": [
    "RedHatAI/granite-3.1-8b-instruct",
    "microsoft/DialoGPT-large",
    "gpt2"
  ],
  "config": {
    "max_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50
  }
}
```

## Request/Response Schemas

### Query Request Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Natural language query to process",
      "minLength": 1,
      "maxLength": 1000,
      "example": "What is OpenShift and how does it work?"
    },
    "top_k": {
      "type": "integer",
      "description": "Number of documents to retrieve",
      "minimum": 1,
      "maximum": 20,
      "default": 5,
      "example": 3
    },
    "filters": {
      "type": "object",
      "description": "Metadata filters for document retrieval",
      "additionalProperties": true,
      "example": {
        "category": "cloud",
        "source": "openshift_docs",
        "language": "en"
      }
    },
    "model_name": {
      "type": "string",
      "description": "vLLM model to use for generation",
      "default": "RedHatAI/granite-3.1-8b-instruct",
      "example": "microsoft/DialoGPT-large"
    }
  },
  "required": ["query"]
}
```

### Query Response Schema

```json
{
  "type": "object",
  "properties": {
    "answer": {
      "type": "string",
      "description": "Generated answer based on retrieved documents",
      "example": "OpenShift is a Kubernetes platform that provides enterprise-grade container orchestration capabilities..."
    },
    "sources": {
      "type": "array",
      "description": "Source documents used for generation",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string",
            "description": "Document identifier",
            "example": "doc_123"
          },
          "text": {
            "type": "string",
            "description": "Document text content",
            "example": "OpenShift is a Kubernetes platform..."
          },
          "metadata": {
            "type": "object",
            "description": "Document metadata",
            "example": {
              "category": "cloud",
              "source": "openshift_docs",
              "language": "en"
            }
          },
          "score": {
            "type": "number",
            "description": "Relevance score (0-1)",
            "minimum": 0,
            "maximum": 1,
            "example": 0.95
          }
        },
        "required": ["id", "text", "metadata", "score"]
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "model": {
          "type": "string",
          "description": "Model used for generation",
          "example": "RedHatAI/granite-3.1-8b-instruct"
        },
        "latency_ms": {
          "type": "integer",
          "description": "Total request latency in milliseconds",
          "example": 1250
        },
        "query_time_ms": {
          "type": "integer",
          "description": "Query processing time in milliseconds",
          "example": 150
        },
        "retrieval_time_ms": {
          "type": "integer",
          "description": "Document retrieval time in milliseconds",
          "example": 300
        },
        "generation_time_ms": {
          "type": "integer",
          "description": "Text generation time in milliseconds",
          "example": 800
        }
      },
      "required": ["model", "latency_ms"]
    }
  },
  "required": ["answer", "sources", "metadata"]
}
```

### Error Response Schema

```json
{
  "type": "object",
  "properties": {
    "error": {
      "type": "string",
      "description": "Error message",
      "example": "Invalid query parameter"
    },
    "detail": {
      "type": "string",
      "description": "Detailed error information",
      "example": "Query parameter is required and cannot be empty"
    },
    "status_code": {
      "type": "integer",
      "description": "HTTP status code",
      "example": 422
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Error timestamp",
      "example": "2024-01-15T14:30:25Z"
    }
  },
  "required": ["error", "status_code"]
}
```

## Usage Examples

### Basic Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is OpenShift?",
    "top_k": 3
  }'
```

**Response:**
```json
{
  "answer": "OpenShift is a Kubernetes platform that provides enterprise-grade container orchestration capabilities. It offers advanced cluster management, developer tools, and automated operations for hybrid cloud and multicloud deployments.",
  "sources": [
    {
      "id": "doc1",
      "text": "OpenShift is a Kubernetes platform that provides a complete container and Kubernetes platform for enterprises...",
      "metadata": {
        "category": "cloud",
        "source": "openshift_docs"
      },
      "score": 0.95
    },
    {
      "id": "doc2",
      "text": "Red Hat OpenShift is an enterprise-ready Kubernetes container platform with full-stack automated operations...",
      "metadata": {
        "category": "cloud",
        "source": "redhat_docs"
      },
      "score": 0.88
    }
  ],
  "metadata": {
        "model": "RedHatAI/granite-3.1-8b-instruct",
    "latency_ms": 1250,
    "query_time_ms": 150,
    "retrieval_time_ms": 300,
    "generation_time_ms": 800
  }
}
```

### Query with Filters

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Kubernetes platform",
    "top_k": 2,
    "filters": {
      "category": "cloud",
      "source": "openshift_docs"
    }
  }'
```

### Query with Specific Model

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain RAG technology",
    "top_k": 3,
    "model_name": "microsoft/DialoGPT-large"
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T14:30:25Z",
  "version": "0.1.0"
}
```

### Readiness Check

```bash
curl http://localhost:8000/ready
```

**Response:**
```json
{
  "status": "ready",
  "dependencies": {
    "elasticsearch": "ok",
    "vLLM": "ok",
    "embeddings": "ok"
  },
  "timestamp": "2024-01-15T14:30:25Z"
}
```

### Error Handling Examples

#### Missing Query Parameter

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "top_k": 3
  }'
```

**Response:**
```json
{
  "error": "Validation Error",
  "detail": "Query parameter is required",
  "status_code": 422,
  "timestamp": "2024-01-15T14:30:25Z"
}
```

#### Invalid JSON

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d 'invalid json'
```

**Response:**
```json
{
  "error": "JSON Decode Error",
  "detail": "Invalid JSON format",
  "status_code": 422,
  "timestamp": "2024-01-15T14:30:25Z"
}
```

#### Service Unavailable

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test query"
  }'
```

**Response:**
```json
{
  "error": "Service Unavailable",
  "detail": "ElasticSearch connection failed",
  "status_code": 503,
  "timestamp": "2024-01-15T14:30:25Z"
}
```

## Model Configuration

### Available Models

The API supports various vLLM-compatible models. Check available models using the `/api/v1/info` endpoint.

**Common Models:**
- `RedHatAI/granite-3.1-8b-instruct` (default)
- `microsoft/DialoGPT-large`
- `gpt2`
- `gpt2-medium`
- `gpt2-large`

### Model Parameters

**Generation Parameters:**
- `temperature`: Controls randomness (0.0-1.0, default: 0.7)
- `max_tokens`: Maximum tokens to generate (default: 512)
- `top_p`: Nucleus sampling parameter (0.0-1.0, default: 0.9)
- `top_k`: Top-k sampling parameter (default: 50)

**Performance Considerations:**
- Larger models provide better quality but slower inference
- Smaller models are faster but may have lower quality
- Consider your use case requirements for model selection

### Best Practices

1. **Model Selection:**
   - Use `RedHatAI/granite-3.1-8b-instruct` for general queries
   - Use `microsoft/DialoGPT-large` for complex reasoning
   - Test different models for your specific use case

2. **Parameter Tuning:**
   - Lower temperature (0.3-0.5) for factual responses
   - Higher temperature (0.7-0.9) for creative responses
   - Adjust `top_k` based on response quality needs

3. **Performance Optimization:**
   - Use appropriate `top_k` values (3-5 for most cases)
   - Implement caching for repeated queries
   - Monitor response times and adjust accordingly

## Integration Guide

### Service Discovery in OpenShift

```bash
# Get service URL
oc get route rag-api -o jsonpath='{.spec.host}'

# Get service IP
oc get svc rag-api -o jsonpath='{.spec.clusterIP}'

# Port forward for local access
oc port-forward svc/rag-api 8000:8000
```

### Client Integration Examples

#### Python Client

```python
import requests
import json

class RAGAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def query(self, query, top_k=5, filters=None, model_name=None):
        """Send a query to the RAG API."""
        payload = {
            "query": query,
            "top_k": top_k
        }
        
        if filters:
            payload["filters"] = filters
        if model_name:
            payload["model_name"] = model_name
        
        response = requests.post(
            f"{self.base_url}/api/v1/query",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """Check API health."""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    
    def ready_check(self):
        """Check API readiness."""
        response = requests.get(f"{self.base_url}/ready", timeout=5)
        response.raise_for_status()
        return response.json()

# Usage
client = RAGAPIClient("http://localhost:8000")

# Health check
health = client.health_check()
print(f"API Status: {health['status']}")

# Query
result = client.query(
    query="What is OpenShift?",
    top_k=3,
    filters={"category": "cloud"}
)
print(f"Answer: {result['answer']}")
```

#### JavaScript/Node.js Client

```javascript
class RAGAPIClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }
    
    async query(query, topK = 5, filters = null, modelName = null) {
        const payload = {
            query,
            top_k: topK
        };
        
        if (filters) payload.filters = filters;
        if (modelName) payload.model_name = modelName;
        
        const response = await fetch(`${this.baseUrl}/api/v1/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/health`);
        if (!response.ok) {
            throw new Error(`Health check failed: ${response.status}`);
        }
        return await response.json();
    }
    
    async readyCheck() {
        const response = await fetch(`${this.baseUrl}/ready`);
        if (!response.ok) {
            throw new Error(`Ready check failed: ${response.status}`);
        }
        return await response.json();
    }
}

// Usage
const client = new RAGAPIClient('http://localhost:8000');

// Health check
client.healthCheck()
    .then(health => console.log(`API Status: ${health.status}`))
    .catch(error => console.error('Health check failed:', error));

// Query
client.query('What is OpenShift?', 3, { category: 'cloud' })
    .then(result => console.log('Answer:', result.answer))
    .catch(error => console.error('Query failed:', error));
```

#### Go Client

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type RAGAPIClient struct {
    BaseURL string
    Client  *http.Client
}

type QueryRequest struct {
    Query     string                 `json:"query"`
    TopK      int                    `json:"top_k"`
    Filters   map[string]interface{} `json:"filters,omitempty"`
    ModelName string                 `json:"model_name,omitempty"`
}

type QueryResponse struct {
    Answer   string `json:"answer"`
    Sources  []struct {
        ID       string                 `json:"id"`
        Text     string                 `json:"text"`
        Metadata map[string]interface{} `json:"metadata"`
        Score    float64                `json:"score"`
    } `json:"sources"`
    Metadata struct {
        Model    string `json:"model"`
        Latency  int    `json:"latency_ms"`
    } `json:"metadata"`
}

func NewRAGAPIClient(baseURL string) *RAGAPIClient {
    return &RAGAPIClient{
        BaseURL: baseURL,
        Client: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

func (c *RAGAPIClient) Query(req QueryRequest) (*QueryResponse, error) {
    jsonData, err := json.Marshal(req)
    if err != nil {
        return nil, err
    }
    
    resp, err := c.Client.Post(
        c.BaseURL+"/api/v1/query",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("API error: %d", resp.StatusCode)
    }
    
    var result QueryResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }
    
    return &result, nil
}

func main() {
    client := NewRAGAPIClient("http://localhost:8000")
    
    result, err := client.Query(QueryRequest{
        Query: "What is OpenShift?",
        TopK:  3,
        Filters: map[string]interface{}{
            "category": "cloud",
        },
    })
    
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    
    fmt.Printf("Answer: %s\n", result.Answer)
}
```

### Error Handling Recommendations

1. **Implement Retry Logic:**
   ```python
   import time
   from requests.exceptions import RequestException
   
   def query_with_retry(client, query, max_retries=3, delay=1):
       for attempt in range(max_retries):
           try:
               return client.query(query)
           except RequestException as e:
               if attempt == max_retries - 1:
                   raise
               time.sleep(delay * (2 ** attempt))  # Exponential backoff
   ```

2. **Handle Different Error Types:**
   ```python
   try:
       result = client.query(query)
   except requests.exceptions.Timeout:
       # Handle timeout
       pass
   except requests.exceptions.ConnectionError:
       # Handle connection error
       pass
   except requests.exceptions.HTTPError as e:
       if e.response.status_code == 503:
           # Service unavailable
           pass
       elif e.response.status_code == 422:
           # Validation error
           pass
   ```

3. **Circuit Breaker Pattern:**
   ```python
   class CircuitBreaker:
       def __init__(self, failure_threshold=5, timeout=60):
           self.failure_threshold = failure_threshold
           self.timeout = timeout
           self.failure_count = 0
           self.last_failure_time = None
           self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
       
       def call(self, func, *args, **kwargs):
           if self.state == "OPEN":
               if time.time() - self.last_failure_time > self.timeout:
                   self.state = "HALF_OPEN"
               else:
                   raise Exception("Circuit breaker is OPEN")
           
           try:
               result = func(*args, **kwargs)
               self.failure_count = 0
               self.state = "CLOSED"
               return result
           except Exception as e:
               self.failure_count += 1
               self.last_failure_time = time.time()
               if self.failure_count >= self.failure_threshold:
                   self.state = "OPEN"
               raise
   ```

### Performance Optimization Tips

1. **Connection Pooling:**
   ```python
   import requests
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry
   
   session = requests.Session()
   adapter = HTTPAdapter(
       pool_connections=10,
       pool_maxsize=20,
       max_retries=Retry(total=3, backoff_factor=0.1)
   )
   session.mount('http://', adapter)
   session.mount('https://', adapter)
   ```

2. **Request Batching:**
   ```python
   async def batch_queries(client, queries, batch_size=5):
       results = []
       for i in range(0, len(queries), batch_size):
           batch = queries[i:i + batch_size]
           tasks = [client.query(q) for q in batch]
           batch_results = await asyncio.gather(*tasks)
           results.extend(batch_results)
       return results
   ```

3. **Caching:**
   ```python
   import hashlib
   import json
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def cached_query(query, top_k, filters_str):
       filters = json.loads(filters_str) if filters_str else None
       return client.query(query, top_k, filters)
   
   # Usage
   filters_str = json.dumps({"category": "cloud"})
   result = cached_query("What is OpenShift?", 3, filters_str)
   ```

## Troubleshooting & Common Issues

This section documents real-world issues encountered during deployment and integration, along with their solutions.

### 1. Double Prefix in API Routes (404 Errors)
**Symptom:** All API endpoints return 404, and OpenAPI docs show double prefix (e.g., `/api/api/v1/query`).

**Solution:**
- Ensure FastAPI routers are included with the correct `prefix` and that no double prefixing occurs in `main.py` or `routes.py`.
- Example fix:
  ```python
  # main.py
  app.include_router(api_router, prefix="/api/v1")
  # routes.py
  router = APIRouter()
  # ...
  ```

### 2. Health/Readiness Checks Failing
**Symptom:** Liveness/readiness probes fail, pod marked as not ready.

**Solution:**
- Ensure `/health` and `/ready` endpoints return correct status and are not protected by auth.
- Adjust `readinessProbe` in deployment YAML to match the correct path and port.
- Example:
  ```yaml
  readinessProbe:
    httpGet:
      path: /ready
      port: 8000
  ```

### 3. Logging Errors & Generic Error Messages
**Symptom:** API returns generic error, logs show `TypeError` in logging calls.

**Solution:**
- Fix logging calls to use correct arguments (avoid unexpected keyword arguments).
- Improve error handling to log and return meaningful messages.
- Example:
  ```python
  logging.error("Error in agent: %s", str(e))
  ```

### 4. DocumentSource Validation Error (score > 1, document None)
**Symptom:** API returns validation error, logs show `score` > 1 or `document` is None.

**Solution:**
- Normalize score to max 1.0 (e.g., `min(raw_score / 2.0, 1.0)`).
- Use `document = "Unknown"` if missing.
- Example:
  ```python
  normalized_score = min(raw_score / 2.0, 1.0)
  document_name = doc.metadata.get("document_name") or "Unknown"
  ```

### 5. Container Image Not Updating Code
**Symptom:** Pod runs old code even after rebuild.

**Solution:**
- Force Docker/Podman build without cache:
  ```bash
  podman build --no-cache -f Containerfile -t rag-openshift-ai-api:dev-X .
  ```
- Uninstall and reinstall Helm release to ensure new image is used:
  ```bash
  helm uninstall rag-openshift-ai-api -n rag-openshift-ai
  helm install rag-openshift-ai-api ./helm -n rag-openshift-ai
  ```

### 6. Test Script Detects Wrong Route
**Symptom:** `test-api.sh` script uses wrong endpoint or fails health check.

**Solution:**
- Remove auto-detection logic and set `API_ENDPOINT` manually at the top of the script.
- Or pass with `-e` argument:
  ```bash
  ./scripts/test-api.sh -e "http://your-api-url" -v
  ```

For more troubleshooting tips, see the logs and check the deployment YAMLs for correct configuration.

## Performance Optimization

### 1. Query Optimization

**Best Practices:**
- Use appropriate `top_k` values (3-5 for most cases)
- Implement query caching
- Use metadata filters to reduce search space
- Optimize ElasticSearch index configuration

**Example:**
```python
# Optimized query with filters
result = client.query(
    query="OpenShift deployment",
    top_k=3,
    filters={
        "category": "cloud",
        "source": "openshift_docs"
    }
)
```

### 2. Caching Strategies

**Response Caching:**
```python
import redis
import hashlib
import json

class CachedRAGClient:
    def __init__(self, base_url, redis_url="redis://localhost:6379"):
        self.client = RAGAPIClient(base_url)
        self.redis = redis.from_url(redis_url)
    
    def query(self, query, top_k=5, filters=None, ttl=3600):
        # Create cache key
        cache_key = self._create_cache_key(query, top_k, filters)
        
        # Check cache
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Query API
        result = self.client.query(query, top_k, filters)
        
        # Cache result
        self.redis.setex(cache_key, ttl, json.dumps(result))
        
        return result
    
    def _create_cache_key(self, query, top_k, filters):
        data = f"{query}:{top_k}:{json.dumps(filters, sort_keys=True)}"
        return f"rag:query:{hashlib.md5(data.encode()).hexdigest()}"
```

### 3. Connection Pooling

**HTTP Connection Pooling:**
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    session = requests.Session()
    
    # Configure connection pooling
    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=Retry(total=3, backoff_factor=0.1)
    )
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session

# Usage
session = create_session()
client = RAGAPIClient("http://localhost:8000", session=session)
```

### 4. Async Processing

**Concurrent Requests:**
```python
import asyncio
import aiohttp

class AsyncRAGClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    async def query(self, query, top_k=5, filters=None):
        async with aiohttp.ClientSession() as session:
            payload = {
                "query": query,
                "top_k": top_k
            }
            if filters:
                payload["filters"] = filters
            
            async with session.post(
                f"{self.base_url}/api/v1/query",
                json=payload
            ) as response:
                return await response.json()
    
    async def batch_query(self, queries, batch_size=5):
        results = []
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            tasks = [self.query(q) for q in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        return results

# Usage
async def main():
    client = AsyncRAGClient("http://localhost:8000")
    queries = ["What is OpenShift?", "How does Kubernetes work?"]
    results = await client.batch_query(queries)
    print(results)

asyncio.run(main())
```

## API Reference

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 422 | Unprocessable Entity (validation error) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Rate Limiting

Currently, the API does not implement rate limiting. Consider implementing rate limiting for production deployments.

### Request Limits

- **Query Length**: Maximum 1000 characters
- **Top K**: Maximum 20 documents
- **Request Size**: Maximum 1MB
- **Timeout**: 30 seconds (configurable)

### Response Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json` |
| `X-Request-ID` | Unique request identifier |
| `X-Response-Time` | Response time in milliseconds |

### Monitoring and Metrics

The API exposes Prometheus metrics at `/api/v1/metrics`:

- `rag_api_requests_total`: Total request count
- `rag_api_request_duration_seconds`: Request duration histogram
- `rag_retrieval_documents_total`: Total documents retrieved
- `rag_generation_tokens_total`: Total tokens generated

### Health Check Endpoints

- `/health`: Basic health status
- `/ready`: Service readiness with dependency checks
- `/api/v1/metrics`: Prometheus metrics
- `/api/v1/info`: API information and configuration

## 📚 Additional Documentation

- [Helm Installation Guide](HELM_INSTALLATION.md) - Complete Helm deployment guide
- [OpenShift Deployment](OPENSHIFT.md) - Manual OpenShift deployment instructions
- [Container Guide](CONTAINER.md) - Container build and optimization guide
- [API Testing](API_TESTING.md) - Testing strategies and examples

## Support

For additional support or questions, please refer to the project documentation or contact the development team. 