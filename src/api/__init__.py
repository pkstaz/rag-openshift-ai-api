"""
FastAPI Application Package

This package contains the FastAPI application, routes, and API endpoints
for the RAG agent service.
"""

# from .app import create_app  # Will be created in next step
from .models import (
    QueryRequest,
    QueryResponse,
    DocumentSource,
    QueryMetadata,
    HealthResponse,
    ErrorResponse,
    StreamlitQueryRequest,
    StreamlitQueryResponse,
    LLMParams,
    RetrievalParams,
    ComponentStatus,
    InfoResponse,
    ModelInfo,
    SimpleHealthResponse
)

from .routes import router

__all__ = [
    # "create_app",  # Will be created in next step
    "QueryRequest",
    "QueryResponse", 
    "DocumentSource",
    "QueryMetadata",
    "HealthResponse",
    "ErrorResponse",
    "StreamlitQueryRequest",
    "StreamlitQueryResponse",
    "LLMParams",
    "RetrievalParams",
    "ComponentStatus",
    "InfoResponse",
    "ModelInfo",
    "SimpleHealthResponse",
    "router"
] 