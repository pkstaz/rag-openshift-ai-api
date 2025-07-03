"""
End-to-End Integration Tests

This module contains comprehensive integration tests that validate the complete
RAG pipeline with real services including ElasticSearch and vLLM.
"""

import pytest
import asyncio
import time
import json
import os
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

import requests
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
import numpy as np

from src.main import app
from src.config.settings import settings
from src.rag.agent import RAGAgent
from src.rag.embeddings import EmbeddingManager
from src.rag.retriever import ElasticSearchRetriever


# ----------------------
# Test Configuration
# ----------------------
class IntegrationTestConfig:
    """Configuration for integration tests."""
    
    # Test data
    TEST_DOCUMENTS = [
        {
            "id": "doc1",
            "text": "OpenShift is a Kubernetes platform that provides a complete container and Kubernetes platform for enterprises. It offers advanced cluster management capabilities and developer tools.",
            "metadata": {
                "category": "cloud",
                "source": "openshift_docs",
                "language": "en"
            }
        },
        {
            "id": "doc2", 
            "text": "Red Hat OpenShift is an enterprise-ready Kubernetes container platform with full-stack automated operations to manage hybrid cloud and multicloud deployments.",
            "metadata": {
                "category": "cloud",
                "source": "redhat_docs",
                "language": "en"
            }
        },
        {
            "id": "doc3",
            "text": "Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications.",
            "metadata": {
                "category": "container",
                "source": "kubernetes_docs",
                "language": "en"
            }
        },
        {
            "id": "doc4",
            "text": "RAG (Retrieval-Augmented Generation) combines information retrieval with text generation to provide more accurate and contextual responses to user queries.",
            "metadata": {
                "category": "ai",
                "source": "ai_docs",
                "language": "en"
            }
        },
        {
            "id": "doc5",
            "text": "Elasticsearch is a distributed search and analytics engine that provides fast search capabilities and real-time analytics for structured and unstructured data.",
            "metadata": {
                "category": "search",
                "source": "elasticsearch_docs",
                "language": "en"
            }
        }
    ]
    
    # Performance thresholds
    MAX_QUERY_LATENCY_MS = 5000  # 5 seconds
    MAX_CONCURRENT_QUERIES = 10
    MIN_THROUGHPUT_RPS = 2  # 2 requests per second minimum
    
    # Test queries
    TEST_QUERIES = [
        "What is OpenShift?",
        "How does Kubernetes work?",
        "Explain RAG technology",
        "What is Elasticsearch used for?",
        "Compare OpenShift and Kubernetes"
    ]
    
    # Expected response patterns
    EXPECTED_KEYWORDS = {
        "openshift": ["kubernetes", "platform", "enterprise"],
        "kubernetes": ["container", "orchestration", "deployment"],
        "rag": ["retrieval", "generation", "contextual"],
        "elasticsearch": ["search", "analytics", "distributed"]
    }


# ----------------------
# Fixtures & Setup
# ----------------------
@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return IntegrationTestConfig()


@pytest.fixture(scope="session")
def elasticsearch_client():
    """Elasticsearch client fixture."""
    try:
        es = Elasticsearch(
            [settings.elasticsearch.url],
            basic_auth=(settings.elasticsearch.username, settings.elasticsearch.password) if settings.elasticsearch.username else None,
            timeout=settings.elasticsearch.timeout,
            retry_on_timeout=settings.elasticsearch.retry_on_timeout,
            max_retries=settings.elasticsearch.max_retries
        )
        
        # Test connection
        if not es.ping():
            pytest.skip("Elasticsearch not available")
        
        return es
    except Exception as e:
        pytest.skip(f"Elasticsearch connection failed: {e}")


@pytest.fixture(scope="session")
def vllm_client():
    """vLLM client fixture."""
    try:
        # Test vLLM connection
        response = requests.get(f"{settings.vllm.url}/v1/models", timeout=10)
        if response.status_code != 200:
            pytest.skip("vLLM not available")
        
        return settings.vllm.url
    except Exception as e:
        pytest.skip(f"vLLM connection failed: {e}")


@pytest.fixture(scope="session")
def test_index_name():
    """Test index name fixture."""
    return f"{settings.elasticsearch.index_name}_test_{int(time.time())}"


@pytest.fixture(scope="session")
def setup_test_environment(elasticsearch_client, test_index_name, test_config):
    """Setup test environment with test data."""
    es = elasticsearch_client
    
    # Create test index
    index_mapping = {
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "metadata": {"type": "object"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": settings.elasticsearch.vector_dimension
                }
            }
        }
    }
    
    try:
        es.indices.create(index=test_index_name, body=index_mapping)
    except Exception as e:
        if "resource_already_exists_exception" not in str(e):
            raise e
    
    # Generate embeddings and index test documents
    embedding_manager = EmbeddingManager()
    
    for doc in test_config.TEST_DOCUMENTS:
        # Generate embedding
        embedding = embedding_manager.get_embedding(doc["text"])
        
        # Index document
        es.index(
            index=test_index_name,
            id=doc["id"],
            body={
                "text": doc["text"],
                "metadata": doc["metadata"],
                "embedding": embedding.tolist()
            }
        )
    
    # Refresh index
    es.indices.refresh(index=test_index_name)
    
    yield test_index_name
    
    # Cleanup
    try:
        es.indices.delete(index=test_index_name)
    except Exception:
        pass


@pytest.fixture
def rag_agent(setup_test_environment, test_index_name):
    """RAG Agent fixture with test index."""
    # Temporarily override index name
    original_index = settings.elasticsearch.index_name
    settings.elasticsearch.index_name = test_index_name
    
    agent = RAGAgent()
    
    yield agent
    
    # Restore original index name
    settings.elasticsearch.index_name = original_index


@pytest.fixture
def api_client():
    """FastAPI test client fixture."""
    return TestClient(app)


# ----------------------
# 1. Full RAG Pipeline Tests
# ----------------------
class TestFullRAGPipeline:
    """Test complete RAG pipeline with real services."""
    
    def test_rag_query_with_real_elasticsearch(self, rag_agent, test_config):
        """Test RAG query using real Elasticsearch."""
        query = "What is OpenShift?"
        
        response = rag_agent.query(
            query=query,
            top_k=3,
            filters={"category": "cloud"}
        )
        
        # Validate response structure
        assert "answer" in response
        assert "sources" in response
        assert "metadata" in response
        
        # Validate answer quality
        assert len(response["answer"]) > 50
        assert any(keyword.lower() in response["answer"].lower() 
                  for keyword in ["openshift", "kubernetes", "platform"])
        
        # Validate sources
        assert len(response["sources"]) > 0
        assert len(response["sources"]) <= 3
        
        for source in response["sources"]:
            assert "id" in source
            assert "text" in source
            assert "metadata" in source
            assert "score" in source
        
        # Validate metadata
        assert "model" in response["metadata"]
        assert "latency_ms" in response["metadata"]
        assert response["metadata"]["latency_ms"] > 0
    
    def test_rag_query_with_real_vllm(self, rag_agent, test_config):
        """Test RAG query using real vLLM for generation."""
        query = "Explain how RAG works"
        
        response = rag_agent.query(
            query=query,
            top_k=2,
            model_name=settings.vllm.model_name
        )
        
        # Validate generation quality
        assert len(response["answer"]) > 100
        assert any(keyword.lower() in response["answer"].lower() 
                  for keyword in ["retrieval", "generation", "context"])
        
        # Validate source relevance
        relevant_sources = [s for s in response["sources"] 
                          if "rag" in s["text"].lower() or "retrieval" in s["text"].lower()]
        assert len(relevant_sources) > 0
    
    def test_complete_rag_flow(self, rag_agent, test_config):
        """Test complete end-to-end RAG flow."""
        queries = test_config.TEST_QUERIES[:3]  # Test first 3 queries
        
        for query in queries:
            response = rag_agent.query(query=query, top_k=2)
            
            # Basic validation
            assert "answer" in response
            assert "sources" in response
            assert len(response["sources"]) > 0
            
            # Answer quality check
            assert len(response["answer"]) > 30
            
            # Source relevance check
            query_keywords = query.lower().split()
            relevant_sources = 0
            
            for source in response["sources"]:
                source_text = source["text"].lower()
                if any(keyword in source_text for keyword in query_keywords):
                    relevant_sources += 1
            
            assert relevant_sources > 0
    
    def test_multiple_queries_performance(self, rag_agent, test_config):
        """Test performance with multiple queries."""
        queries = test_config.TEST_QUERIES
        
        start_time = time.time()
        responses = []
        
        for query in queries:
            response = rag_agent.query(query=query, top_k=2)
            responses.append(response)
        
        total_time = time.time() - start_time
        avg_time = total_time / len(queries)
        
        # Performance validation
        assert avg_time < (test_config.MAX_QUERY_LATENCY_MS / 1000)
        assert len(responses) == len(queries)
        
        # All responses should be valid
        for response in responses:
            assert "answer" in response
            assert "sources" in response


# ----------------------
# 2. ElasticSearch Integration Tests
# ----------------------
class TestElasticSearchIntegration:
    """Test ElasticSearch integration functionality."""
    
    def test_elasticsearch_connection(self, elasticsearch_client):
        """Test ElasticSearch connectivity."""
        es = elasticsearch_client
        
        # Test basic connection
        assert es.ping()
        
        # Test cluster info
        info = es.info()
        assert "version" in info
        assert "cluster_name" in info
    
    def test_elasticsearch_search_query(self, elasticsearch_client, setup_test_environment, test_index_name):
        """Test vector search functionality."""
        es = elasticsearch_client
        embedding_manager = EmbeddingManager()
        
        # Test query
        query_text = "OpenShift platform"
        query_embedding = embedding_manager.get_embedding(query_text)
        
        # Vector search
        search_body = {
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding.tolist()}
                    }
                }
            },
            "size": 3
        }
        
        results = es.search(index=test_index_name, body=search_body)
        
        # Validate results
        assert "hits" in results
        assert "hits" in results["hits"]
        assert len(results["hits"]["hits"]) > 0
        
        # Check relevance scores
        for hit in results["hits"]["hits"]:
            assert "_score" in hit
            assert hit["_score"] > 0
    
    def test_elasticsearch_index_structure(self, elasticsearch_client, setup_test_environment, test_index_name):
        """Test index schema validation."""
        es = elasticsearch_client
        
        # Get index mapping
        mapping = es.indices.get_mapping(index=test_index_name)
        
        # Validate structure
        properties = mapping[test_index_name]["mappings"]["properties"]
        
        assert "text" in properties
        assert "metadata" in properties
        assert "embedding" in properties
        
        # Validate embedding field
        embedding_field = properties["embedding"]
        assert embedding_field["type"] == "dense_vector"
        assert embedding_field["dims"] == settings.elasticsearch.vector_dimension
    
    def test_elasticsearch_error_handling(self, elasticsearch_client):
        """Test ElasticSearch error handling."""
        es = elasticsearch_client
        
        # Test invalid index
        try:
            es.search(index="nonexistent_index", body={"query": {"match_all": {}}})
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "index_not_found_exception" in str(e) or "404" in str(e)
        
        # Test invalid query
        try:
            es.search(index="_all", body={"invalid": "query"})
            assert False, "Should have raised an exception"
        except Exception:
            # This should raise some kind of exception
            pass


# ----------------------
# 3. vLLM Integration Tests
# ----------------------
class TestVLLMIntegration:
    """Test vLLM integration functionality."""
    
    def test_vllm_connection(self, vllm_client):
        """Test vLLM service availability."""
        url = vllm_client
        
        # Test models endpoint
        response = requests.get(f"{url}/v1/models", timeout=10)
        assert response.status_code == 200
        
        # Test health endpoint if available
        try:
            health_response = requests.get(f"{url}/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                assert "status" in health_data
        except Exception:
            # Health endpoint might not be available
            pass
    
    def test_vllm_model_list(self, vllm_client):
        """Test available models endpoint."""
        url = vllm_client
        
        response = requests.get(f"{url}/v1/models", timeout=10)
        data = response.json()
        
        assert "data" in data
        assert len(data["data"]) > 0
        
        # Check model structure
        model = data["data"][0]
        assert "id" in model
        assert "object" in model
        assert model["object"] == "model"
    
    def test_vllm_generation(self, vllm_client):
        """Test text generation with vLLM."""
        url = vllm_client
        
        # Get available models
        models_response = requests.get(f"{url}/v1/models", timeout=10)
        models_data = models_response.json()
        
        if not models_data["data"]:
            pytest.skip("No models available in vLLM")
        
        model_id = models_data["data"][0]["id"]
        
        # Test generation
        generation_data = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "What is artificial intelligence?"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{url}/v1/chat/completions",
            json=generation_data,
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "choices" in data
        assert len(data["choices"]) > 0
        
        choice = data["choices"][0]
        assert "message" in choice
        assert "content" in choice["message"]
        assert len(choice["message"]["content"]) > 0
    
    def test_vllm_different_models(self, vllm_client):
        """Test multiple model support."""
        url = vllm_client
        
        # Get available models
        response = requests.get(f"{url}/v1/models", timeout=10)
        data = response.json()
        
        if len(data["data"]) < 2:
            pytest.skip("Less than 2 models available")
        
        # Test each model
        for model in data["data"][:2]:  # Test first 2 models
            model_id = model["id"]
            
            generation_data = {
                "model": model_id,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 50
            }
            
            try:
                response = requests.post(
                    f"{url}/v1/chat/completions",
                    json=generation_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    assert "choices" in data
                    assert len(data["choices"]) > 0
            except Exception as e:
                # Some models might not support chat completions
                pytest.skip(f"Model {model_id} not compatible: {e}")


# ----------------------
# 4. Performance Tests
# ----------------------
class TestPerformance:
    """Test performance characteristics."""
    
    def test_query_latency(self, rag_agent, test_config):
        """Test query response time."""
        query = "What is OpenShift?"
        
        start_time = time.time()
        response = rag_agent.query(query=query, top_k=2)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Validate latency
        assert latency_ms < test_config.MAX_QUERY_LATENCY_MS
        assert "metadata" in response
        assert "latency_ms" in response["metadata"]
        
        # Compare measured vs reported latency
        reported_latency = response["metadata"]["latency_ms"]
        assert abs(latency_ms - reported_latency) < 100  # Allow 100ms difference
    
    def test_concurrent_queries(self, rag_agent, test_config):
        """Test multiple simultaneous requests."""
        queries = test_config.TEST_QUERIES[:test_config.MAX_CONCURRENT_QUERIES]
        
        def make_query(query):
            start_time = time.time()
            response = rag_agent.query(query=query, top_k=2)
            end_time = time.time()
            return {
                "query": query,
                "response": response,
                "latency": (end_time - start_time) * 1000
            }
        
        # Execute queries concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=test_config.MAX_CONCURRENT_QUERIES) as executor:
            futures = [executor.submit(make_query, query) for query in queries]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Validate results
        assert len(results) == len(queries)
        
        # Check all responses are valid
        for result in results:
            assert "response" in result
            assert "answer" in result["response"]
            assert "sources" in result["response"]
            assert result["latency"] < test_config.MAX_QUERY_LATENCY_MS
        
        # Calculate throughput
        throughput = len(queries) / total_time
        assert throughput >= test_config.MIN_THROUGHPUT_RPS
    
    def test_memory_usage(self, rag_agent):
        """Test memory consumption during queries."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run multiple queries
        queries = ["What is OpenShift?", "How does Kubernetes work?", "Explain RAG"]
        
        for query in queries:
            response = rag_agent.query(query=query, top_k=2)
            assert "answer" in response
        
        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100
    
    def test_throughput(self, rag_agent, test_config):
        """Test requests per second throughput."""
        queries = test_config.TEST_QUERIES * 2  # 10 queries total
        
        start_time = time.time()
        
        for query in queries:
            response = rag_agent.query(query=query, top_k=2)
            assert "answer" in response
        
        total_time = time.time() - start_time
        throughput = len(queries) / total_time
        
        # Validate throughput
        assert throughput >= test_config.MIN_THROUGHPUT_RPS
        
        # Log performance metrics
        print(f"\nPerformance Results:")
        print(f"Total queries: {len(queries)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} RPS")
        print(f"Average latency: {(total_time/len(queries)*1000):.2f}ms")


# ----------------------
# 5. API Integration Tests
# ----------------------
class TestAPIIntegration:
    """Test API endpoints with real services."""
    
    def test_api_query_endpoint_integration(self, api_client, setup_test_environment, test_index_name):
        """Test API query endpoint with real services."""
        # Temporarily override index name
        original_index = settings.elasticsearch.index_name
        settings.elasticsearch.index_name = test_index_name
        
        try:
            query_data = {
                "query": "What is OpenShift?",
                "top_k": 2,
                "filters": {"category": "cloud"}
            }
            
            response = api_client.post("/api/v1/query", json=query_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "answer" in data
            assert "sources" in data
            assert "metadata" in data
            
            # Validate answer quality
            assert len(data["answer"]) > 50
            
            # Validate sources
            assert len(data["sources"]) > 0
            assert len(data["sources"]) <= 2
            
        finally:
            # Restore original index name
            settings.elasticsearch.index_name = original_index
    
    def test_api_health_endpoints_integration(self, api_client):
        """Test health endpoints with real services."""
        # Health check
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        
        # Ready check
        response = api_client.get("/ready")
        # Should be 200 if all services are available, 503 otherwise
        assert response.status_code in [200, 503]
        
        # Metrics endpoint
        response = api_client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert "# HELP" in response.text
    
    def test_api_error_handling_integration(self, api_client):
        """Test API error handling with real services."""
        # Invalid query
        response = api_client.post("/api/v1/query", json={})
        assert response.status_code == 422
        
        # Invalid JSON
        response = api_client.post("/api/v1/query", data="invalid json")
        assert response.status_code == 422
        
        # Non-existent endpoint
        response = api_client.get("/api/v1/nonexistent")
        assert response.status_code == 404


# ----------------------
# 6. Test Utilities
# ----------------------
class TestUtilities:
    """Utility functions for testing."""
    
    @staticmethod
    def validate_response_structure(response: Dict[str, Any]) -> bool:
        """Validate response structure."""
        required_fields = ["answer", "sources", "metadata"]
        return all(field in response for field in required_fields)
    
    @staticmethod
    def validate_source_structure(source: Dict[str, Any]) -> bool:
        """Validate source document structure."""
        required_fields = ["id", "text", "metadata", "score"]
        return all(field in source for field in required_fields)
    
    @staticmethod
    def calculate_response_quality(response: Dict[str, Any], query: str) -> float:
        """Calculate response quality score."""
        if not response.get("answer") or not response.get("sources"):
            return 0.0
        
        # Simple quality metrics
        answer_length = len(response["answer"])
        source_count = len(response["sources"])
        avg_source_score = sum(s.get("score", 0) for s in response["sources"]) / source_count if source_count > 0 else 0
        
        # Normalize scores
        length_score = min(answer_length / 100, 1.0)  # Prefer longer answers up to 100 chars
        source_score = min(source_count / 5, 1.0)  # Prefer more sources up to 5
        relevance_score = min(avg_source_score, 1.0)  # Prefer higher relevance scores
        
        return (length_score + source_score + relevance_score) / 3


# ----------------------
# 7. Test Configuration
# ----------------------
def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "elasticsearch: marks tests that require ElasticSearch"
    )
    config.addinivalue_line(
        "markers", "vllm: marks tests that require vLLM"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add integration marker to all tests in this module
        item.add_marker(pytest.mark.integration)
        
        # Add specific markers based on test class
        if "ElasticSearch" in item.name:
            item.add_marker(pytest.mark.elasticsearch)
        elif "VLLM" in item.name:
            item.add_marker(pytest.mark.vllm)
        elif "Performance" in item.name:
            item.add_marker(pytest.mark.performance)


# ----------------------
# 8. Environment Setup
# ----------------------
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment
    os.environ["ENV_ENVIRONMENT"] = "test"
    os.environ["API_DEBUG"] = "true"
    
    # Use test-specific settings
    os.environ["ES_INDEX_NAME"] = "rag_documents_test"
    os.environ["VLLM_TIMEOUT"] = "30"
    os.environ["RAG_TOP_K"] = "3"


def teardown_test_environment():
    """Cleanup test environment."""
    # Remove test-specific environment variables
    for key in ["ENV_ENVIRONMENT", "API_DEBUG", "ES_INDEX_NAME", "VLLM_TIMEOUT", "RAG_TOP_K"]:
        os.environ.pop(key, None)


# Setup and teardown
setup_test_environment() 