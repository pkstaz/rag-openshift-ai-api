"""
Integration Tests Configuration

This module provides shared fixtures and configuration for integration tests.
"""

import pytest
import os
import time
import tempfile
import shutil
from typing import Generator, Dict, Any
from unittest.mock import patch

import requests
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient

from src.main import app
from src.config.settings import settings


# ----------------------
# Environment Configuration
# ----------------------
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Store original environment
    original_env = {}
    for key in ["ENV_ENVIRONMENT", "API_DEBUG", "ES_INDEX_NAME", "VLLM_TIMEOUT", "RAG_TOP_K"]:
        original_env[key] = os.environ.get(key)
    
    # Set test environment
    os.environ["ENV_ENVIRONMENT"] = "test"
    os.environ["API_DEBUG"] = "true"
    os.environ["ES_INDEX_NAME"] = "rag_documents_test"
    os.environ["VLLM_TIMEOUT"] = "30"
    os.environ["RAG_TOP_K"] = "3"
    
    yield
    
    # Restore original environment
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


# ----------------------
# Service Availability Checks
# ----------------------
@pytest.fixture(scope="session")
def elasticsearch_available() -> bool:
    """Check if Elasticsearch is available."""
    try:
        es = Elasticsearch(
            [settings.elasticsearch.url],
            basic_auth=(settings.elasticsearch.username, settings.elasticsearch.password) if settings.elasticsearch.username else None,
            timeout=5
        )
        return es.ping()
    except Exception:
        return False


@pytest.fixture(scope="session")
def vllm_available() -> bool:
    """Check if vLLM is available."""
    try:
        response = requests.get(f"{settings.vllm.url}/v1/models", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# ----------------------
# Test Data Management
# ----------------------
@pytest.fixture(scope="session")
def test_data_dir() -> Generator[str, None, None]:
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="rag_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_documents() -> Dict[str, Any]:
    """Test documents for integration tests."""
    return {
        "documents": [
            {
                "id": "doc1",
                "text": "OpenShift is a Kubernetes platform that provides a complete container and Kubernetes platform for enterprises. It offers advanced cluster management capabilities and developer tools.",
                "metadata": {
                    "category": "cloud",
                    "source": "openshift_docs",
                    "language": "en",
                    "tags": ["kubernetes", "container", "enterprise"]
                }
            },
            {
                "id": "doc2", 
                "text": "Red Hat OpenShift is an enterprise-ready Kubernetes container platform with full-stack automated operations to manage hybrid cloud and multicloud deployments.",
                "metadata": {
                    "category": "cloud",
                    "source": "redhat_docs",
                    "language": "en",
                    "tags": ["redhat", "hybrid", "multicloud"]
                }
            },
            {
                "id": "doc3",
                "text": "Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications.",
                "metadata": {
                    "category": "container",
                    "source": "kubernetes_docs",
                    "language": "en",
                    "tags": ["orchestration", "deployment", "scaling"]
                }
            },
            {
                "id": "doc4",
                "text": "RAG (Retrieval-Augmented Generation) combines information retrieval with text generation to provide more accurate and contextual responses to user queries.",
                "metadata": {
                    "category": "ai",
                    "source": "ai_docs",
                    "language": "en",
                    "tags": ["retrieval", "generation", "ai"]
                }
            },
            {
                "id": "doc5",
                "text": "Elasticsearch is a distributed search and analytics engine that provides fast search capabilities and real-time analytics for structured and unstructured data.",
                "metadata": {
                    "category": "search",
                    "source": "elasticsearch_docs",
                    "language": "en",
                    "tags": ["search", "analytics", "distributed"]
                }
            },
            {
                "id": "doc6",
                "text": "OpenShift AI provides a comprehensive platform for building, training, and deploying machine learning models in enterprise environments with built-in security and governance.",
                "metadata": {
                    "category": "ai",
                    "source": "openshift_ai_docs",
                    "language": "en",
                    "tags": ["machine learning", "training", "deployment"]
                }
            }
        ],
        "queries": [
            "What is OpenShift?",
            "How does Kubernetes work?",
            "Explain RAG technology",
            "What is Elasticsearch used for?",
            "Compare OpenShift and Kubernetes",
            "How does OpenShift AI work?",
            "What are the benefits of container orchestration?",
            "Explain distributed search systems"
        ],
        "expected_patterns": {
            "openshift": ["kubernetes", "platform", "enterprise", "container"],
            "kubernetes": ["container", "orchestration", "deployment", "scaling"],
            "rag": ["retrieval", "generation", "contextual", "information"],
            "elasticsearch": ["search", "analytics", "distributed", "real-time"],
            "ai": ["machine learning", "training", "deployment", "models"]
        }
    }


# ----------------------
# Performance Configuration
# ----------------------
@pytest.fixture(scope="session")
def performance_config() -> Dict[str, Any]:
    """Performance test configuration."""
    return {
        "max_query_latency_ms": 5000,  # 5 seconds
        "max_concurrent_queries": 10,
        "min_throughput_rps": 2,  # 2 requests per second minimum
        "max_memory_increase_mb": 100,
        "concurrent_test_duration": 30,  # seconds
        "load_test_queries": 50
    }


# ----------------------
# Mock Services (for tests that don't need real services)
# ----------------------
@pytest.fixture
def mock_elasticsearch():
    """Mock Elasticsearch for unit-style integration tests."""
    with patch("src.rag.retriever.Elasticsearch") as mock_es:
        # Mock search results
        mock_es.return_value.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "doc1",
                        "_score": 0.95,
                        "_source": {
                            "text": "OpenShift is a Kubernetes platform...",
                            "metadata": {"category": "cloud"}
                        }
                    },
                    {
                        "_id": "doc2",
                        "_score": 0.85,
                        "_source": {
                            "text": "Red Hat OpenShift is an enterprise-ready...",
                            "metadata": {"category": "cloud"}
                        }
                    }
                ]
            }
        }
        yield mock_es


@pytest.fixture
def mock_vllm():
    """Mock vLLM for unit-style integration tests."""
    with patch("src.rag.agent.VLLMOpenAI") as mock_vllm:
        mock_vllm.return_value.agenerate.return_value = {
            "generations": [[{
                "text": "OpenShift is a comprehensive Kubernetes platform that provides enterprise-grade container orchestration capabilities."
            }]]
        }
        yield mock_vllm


# ----------------------
# Test Categories
# ----------------------
def pytest_configure_markers(config):
    """Configure pytest markers for integration tests."""
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
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip based on service availability."""
    for item in items:
        # Add integration marker to all tests in this module
        item.add_marker(pytest.mark.integration)
        
        # Add specific markers based on test class/name
        if "ElasticSearch" in item.name:
            item.add_marker(pytest.mark.elasticsearch)
        elif "VLLM" in item.name:
            item.add_marker(pytest.mark.vllm)
        elif "Performance" in item.name:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "API" in item.name:
            item.add_marker(pytest.mark.api)
        
        # Skip tests based on service availability
        if "elasticsearch" in item.keywords and not config.getoption("--elasticsearch"):
            item.add_marker(pytest.mark.skip(reason="ElasticSearch not available"))
        
        if "vllm" in item.keywords and not config.getoption("--vllm"):
            item.add_marker(pytest.mark.skip(reason="vLLM not available"))


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--elasticsearch",
        action="store_true",
        default=False,
        help="Run tests that require ElasticSearch"
    )
    parser.addoption(
        "--vllm",
        action="store_true",
        default=False,
        help="Run tests that require vLLM"
    )
    parser.addoption(
        "--performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests"
    )


# ----------------------
# Test Reporting
# ----------------------
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Configure test reporting."""
    # Add custom test report
    if config.getoption("--integration"):
        config.option.verbose = 2


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add custom information to test reports."""
    outcome = yield
    report = outcome.get_result()
    
    # Add service availability info
    if hasattr(item.config, "cache"):
        report.service_info = {
            "elasticsearch": item.config.cache.get("elasticsearch_available", False),
            "vllm": item.config.cache.get("vllm_available", False)
        }
    
    # Add performance metrics for performance tests
    if "performance" in item.keywords and call.when == "call":
        if hasattr(call, "duration"):
            report.performance_metrics = {
                "duration": call.duration,
                "memory_usage": getattr(call, "memory_usage", None)
            }


# ----------------------
# Cleanup
# ----------------------
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_resources(test_data_dir):
    """Cleanup test resources after all tests."""
    yield
    # Cleanup is handled by test_data_dir fixture 