import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app

client = TestClient(app)

# ----------------------
# Fixtures & Test Data
# ----------------------
@pytest.fixture
def sample_query():
    return {
        "query": "What is OpenShift?",
        "top_k": 2,
        "filters": {"category": "cloud"}
    }

@pytest.fixture
def sample_query_response():
    return {
        "answer": "OpenShift is a Kubernetes platform...",
        "sources": [
            {"id": "doc1", "text": "OpenShift is...", "metadata": {"category": "cloud"}},
            {"id": "doc2", "text": "Red Hat OpenShift...", "metadata": {"category": "cloud"}}
        ],
        "metadata": {"model": "llama-2", "latency_ms": 123}
    }

# ----------------------
# 1. API Endpoint Tests
# ----------------------
def test_query_endpoint_success(sample_query, sample_query_response):
    with patch("src.rag.agent.RAGAgent.query", return_value=sample_query_response):
        response = client.post("/api/v1/query", json=sample_query)
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert isinstance(data["sources"], list)
        assert data["metadata"]["model"] == "llama-2"

def test_query_endpoint_validation():
    # Missing required 'query' field
    response = client.post("/api/v1/query", json={"top_k": 2})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

# ----------------------
# 2. Health Check Tests
# ----------------------
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ready_endpoint_success():
    with patch("src.rag.agent.RAGAgent.check_dependencies", return_value=True):
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

def test_ready_endpoint_failure():
    with patch("src.rag.agent.RAGAgent.check_dependencies", return_value=False):
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "unavailable"

def test_metrics_endpoint():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "# HELP" in response.text  # Prometheus format

# ----------------------
# 3. Response Schema Tests
# ----------------------
def test_query_response_schema(sample_query, sample_query_response):
    with patch("src.rag.agent.RAGAgent.query", return_value=sample_query_response):
        response = client.post("/api/v1/query", json=sample_query)
        data = response.json()
        assert set(data.keys()) == {"answer", "sources", "metadata"}
        assert isinstance(data["sources"], list)
        for src in data["sources"]:
            assert "id" in src and "text" in src and "metadata" in src

def test_error_response_schema():
    response = client.post("/api/v1/query", json={})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

# ----------------------
# 4. Error Handling Tests
# ----------------------
def test_elasticsearch_connection_error(sample_query):
    with patch("src.rag.agent.RAGAgent.query", side_effect=Exception("Elasticsearch unavailable")):
        response = client.post("/api/v1/query", json=sample_query)
        assert response.status_code == 500
        assert "error" in response.json()

def test_vllm_connection_error(sample_query):
    with patch("src.rag.agent.RAGAgent.query", side_effect=Exception("vLLM unavailable")):
        response = client.post("/api/v1/query", json=sample_query)
        assert response.status_code == 500
        assert "error" in response.json()

def test_invalid_model_parameter(sample_query):
    # Simulate invalid model error
    with patch("src.rag.agent.RAGAgent.query", side_effect=ValueError("Invalid model")):
        response = client.post("/api/v1/query", json=sample_query)
        assert response.status_code == 400
        assert "error" in response.json()

def test_timeout_handling(sample_query):
    # Simulate timeout
    with patch("src.rag.agent.RAGAgent.query", side_effect=TimeoutError("Timeout")):
        response = client.post("/api/v1/query", json=sample_query)
        assert response.status_code == 504
        assert "error" in response.json() 