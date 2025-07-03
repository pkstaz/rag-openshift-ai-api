#!/usr/bin/env python3
"""
RAG OpenShift AI API - Main Application

FastAPI application that provides a REST API for Retrieval-Augmented Generation
using ElasticSearch for document retrieval and vLLM for text generation.
"""

import time
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config.settings import settings
from .utils.logging import (
    setup_logging, get_logger, log_startup_info, 
    log_shutdown_info, get_correlation_id
)
from .utils.metrics import (
    initialize_metrics, start_metrics_server,
    record_error, get_metrics_summary
)
from .rag.agent import initialize_rag_agent, get_rag_health
from .rag.embeddings import initialize_embeddings, get_embedding_health
from .rag.retriever import initialize_retriever, get_retriever_health
from .api.routes import router


# =============================================================================
# Global Variables
# =============================================================================

_startup_time: float = 0.0
_app_logger = None


# =============================================================================
# Application Lifecycle Manager
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    global _startup_time, _app_logger
    
    # Startup
    _startup_time = time.time()
    _app_logger = get_logger("app.lifecycle")
    
    _app_logger.info("Starting RAG OpenShift AI API")
    
    try:
        # Initialize logging
        setup_logging(settings.logging.level)
        _app_logger.info("Logging system initialized")
        
        # Initialize metrics
        initialize_metrics()
        _app_logger.info("Metrics system initialized")
        
        # Start metrics server if enabled
        if settings.metrics.enabled:
            start_metrics_server(
                host=settings.metrics.host,
                port=settings.metrics.port
            )
            _app_logger.info(
                "Metrics server started",
                host=settings.metrics.host,
                port=settings.metrics.port
            )
        
        # Initialize RAG components
        _app_logger.info("Initializing RAG components...")
        
        # Initialize embeddings
        if not initialize_embeddings():
            raise RuntimeError("Failed to initialize embeddings")
        _app_logger.info("Embeddings initialized")
        
        # Initialize retriever
        if not initialize_retriever():
            raise RuntimeError("Failed to initialize retriever")
        _app_logger.info("Retriever initialized")
        
        # Initialize RAG agent
        if not initialize_rag_agent():
            raise RuntimeError("Failed to initialize RAG agent")
        _app_logger.info("RAG agent initialized")
        
        # Validate all components
        _app_logger.info("Validating component health...")
        
        rag_health = get_rag_health()
        if not rag_health["agent_healthy"]:
            raise RuntimeError(f"RAG agent health check failed: {rag_health['errors']}")
        
        embedding_health = get_embedding_health()
        if not embedding_health.get("model_loaded", False):
            raise RuntimeError("Embedding model not loaded")
        
        retriever_health = get_retriever_health()
        if not retriever_health.get("connection_healthy", False):
            raise RuntimeError("Retriever connection unhealthy")
        
        _app_logger.info("All components validated successfully")
        
        # Log startup information
        log_startup_info()
        
        _app_logger.info(
            "RAG OpenShift AI API started successfully",
            version=settings.api.version,
            environment=settings.environment,
            startup_time=time.time() - _startup_time
        )
        
        yield
        
    except Exception as e:
        _app_logger.error(
            "Failed to start application",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc()
        )
        raise
    
    finally:
        # Shutdown
        _app_logger.info("Shutting down RAG OpenShift AI API")
        
        try:
            # Log shutdown information
            log_shutdown_info()
            
            _app_logger.info(
                "RAG OpenShift AI API shutdown completed",
                uptime_seconds=time.time() - _startup_time
            )
            
        except Exception as e:
            _app_logger.error(
                "Error during shutdown",
                error=str(e),
                error_type=type(e).__name__
            )


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="RAG OpenShift AI API",
    description="""
    Retrieval-Augmented Generation API for OpenShift
    
    This API provides intelligent question answering using:
    - **ElasticSearch** for document retrieval
    - **vLLM** for text generation
    - **Sentence Transformers** for embeddings
    
    ## Features
    
    * **RAG Pipeline**: Complete retrieval-augmented generation workflow
    * **Health Monitoring**: Comprehensive health checks and metrics
    * **OpenShift Ready**: Designed for Kubernetes/OpenShift deployment
    * **Observability**: Structured logging and Prometheus metrics
    
    ## Quick Start
    
    1. **Health Check**: `GET /api/v1/health`
    2. **Ask a Question**: `POST /api/v1/query`
    3. **View Metrics**: `GET /api/v1/metrics`
    """,
    version=settings.api.version,
    docs_url="/docs" if settings.api.docs_enabled else None,
    redoc_url="/redoc" if settings.api.docs_enabled else None,
    openapi_url="/openapi.json" if settings.api.docs_enabled else None,
    lifespan=lifespan
)


# =============================================================================
# CORS Middleware
# =============================================================================

if settings.api.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# =============================================================================
# Custom Middleware
# =============================================================================

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to request and response headers."""
    
    # Generate or extract correlation ID
    correlation_id = get_correlation_id()
    
    # Add to request headers
    request.headers.__dict__["_list"].append(
        (b"x-correlation-id", correlation_id.encode())
    )
    
    # Process request
    response = await call_next(request)
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    
    start_time = time.time()
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    logger = get_logger("api.middleware")
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        correlation_id=correlation_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Log successful response
        duration = time.time() - start_time
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            correlation_id=correlation_id,
            status_code=response.status_code,
            duration=duration
        )
        
        return response
        
    except Exception as e:
        # Log failed request
        duration = time.time() - start_time
        logger.error(
            "Request failed",
            method=request.method,
            url=str(request.url),
            correlation_id=correlation_id,
            duration=duration,
            error=str(e),
            error_type=type(e).__name__
        )
        raise


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for all requests."""
    
    start_time = time.time()
    
    try:
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        from .utils.metrics import increment_request_counter, record_request_duration
        
        increment_request_counter(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=str(response.status_code)
        )
        record_request_duration(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=str(response.status_code),
            duration=duration
        )
        
        return response
        
    except Exception as e:
        # Record error metrics
        duration = time.time() - start_time
        from .utils.metrics import increment_request_counter, record_request_duration, record_error
        
        increment_request_counter(
            method=request.method,
            endpoint=str(request.url.path),
            status_code="500"
        )
        record_request_duration(
            method=request.method,
            endpoint=str(request.url.path),
            status_code="500",
            duration=duration
        )
        record_error(type(e).__name__, "api")
        
        raise


# =============================================================================
# Router Registration
# =============================================================================

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["RAG API"])


# =============================================================================
# Root Endpoints
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RAG OpenShift AI API",
        "version": settings.api.version,
        "description": "Retrieval-Augmented Generation API for OpenShift",
        "status": "running",
        "docs": "/docs" if settings.api.docs_enabled else None,
        "health": "/api/v1/health",
        "ready": "/api/v1/ready"
    }


@app.get("/health", tags=["Health"])
async def root_health():
    """Root health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.api.version,
        "service": "rag-api"
    }


# =============================================================================
# Global Exception Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    logger = get_logger("api.errors")
    
    logger.warning(
        "Validation error",
        correlation_id=correlation_id,
        errors=exc.errors()
    )
    
    record_error("ValidationError", "api")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "timestamp": time.time(),
            "correlation_id": correlation_id
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    logger = get_logger("api.errors")
    
    logger.warning(
        "HTTP exception",
        correlation_id=correlation_id,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    record_error("HTTPException", "api")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time(),
            "correlation_id": correlation_id
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    logger = get_logger("api.errors")
    
    logger.error(
        "Unhandled exception",
        correlation_id=correlation_id,
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc()
    )
    
    record_error(type(exc).__name__, "api")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": time.time(),
            "correlation_id": correlation_id
        }
    )


# =============================================================================
# Development Endpoints
# =============================================================================

if settings.environment == "development":
    
    @app.get("/debug/info", tags=["Debug"])
    async def debug_info():
        """Debug information endpoint (development only)."""
        return {
            "app_info": {
                "version": settings.api.version,
                "environment": settings.environment,
                "startup_time": _startup_time,
                "uptime": time.time() - _startup_time
            },
            "settings": {
                "api_host": settings.api.host,
                "api_port": settings.api.port,
                "elasticsearch_url": settings.elasticsearch.url,
                "vllm_url": settings.vllm.url,
                "embedding_model": settings.embeddings.model_name
            },
            "health": {
                "rag_agent": get_rag_health(),
                "embeddings": get_embedding_health(),
                "retriever": get_retriever_health()
            },
            "metrics": get_metrics_summary()
        }
    
    @app.get("/debug/settings", tags=["Debug"])
    async def debug_settings():
        """Debug settings endpoint (development only)."""
        return {
            "api": settings.api.dict(),
            "elasticsearch": settings.elasticsearch.dict(),
            "vllm": settings.vllm.dict(),
            "embeddings": settings.embeddings.dict(),
            "rag": settings.rag.dict(),
            "logging": settings.logging.dict(),
            "metrics": settings.metrics.dict(),
            "environment": settings.environment
        }


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.environment == "development",
        log_level=settings.logging.level.lower(),
        access_log=True
    ) 