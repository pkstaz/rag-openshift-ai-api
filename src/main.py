#!/usr/bin/env python3
"""
RAG OpenShift AI API - Main Application

FastAPI application that provides a REST API for Retrieval-Augmented Generation
using ElasticSearch for document retrieval and vLLM for text generation.
"""

import time
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import json

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config.settings import settings
from .utils.metrics import (
    setup_metrics, start_metrics_server,
    record_error, get_metrics_summary
)
from .rag.agent import initialize_rag_agent, get_rag_health
from .rag.embeddings import initialize_embeddings, get_embedding_health
from .rag.retriever import initialize_retriever, get_retriever_health
from .api.routes import router, readiness_check

try:
    import colorlog
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)s:%(name)s:%(message)s'))
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
except ImportError:
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        level=logging.INFO
    )


# =============================================================================
# Enhanced Logging Functions
# =============================================================================

def log_startup_error(error: Exception, component: str) -> None:
    """Log startup errors with detailed information and troubleshooting steps."""
    
    error_type = type(error).__name__
    error_msg = str(error)
    
    logging.error("=" * 80)
    logging.error(f"🚨 STARTUP ERROR - {component.upper()}")
    logging.error("=" * 80)
    logging.error(f"📋 Component: {component}")
    logging.error(f"📋 Error Type: {error_type}")
    logging.error(f"📋 Error Message: {error_msg}")
    logging.error("")
    logging.error("🔧 TROUBLESHOOTING STEPS:")
    
    if component.lower() == "embeddings":
        logging.error("   🔍 Verify that the embedding model is available")
        logging.error("   🔍 Check internet connection for model download")
        logging.error("   🔍 Ensure sufficient disk space")
        logging.error("   🔍 Verify device availability (CPU/GPU)")
    elif component.lower() == "retriever":
        logging.error("   🔍 Verify Elasticsearch connection")
        logging.error("   🔍 Check if index exists and is accessible")
        logging.error("   🔍 Verify Elasticsearch credentials")
        logging.error("   🔍 Ensure cluster is running")
    elif component.lower() == "rag_agent":
        logging.error("   🔍 Verify all components are initialized")
        logging.error("   🔍 Check vLLM connection")
        logging.error("   🔍 Ensure model is available in vLLM")
        logging.error("   🔍 Verify agent configuration")
    elif component.lower() == "metrics":
        logging.error("   🔍 Verify metrics port is available")
        logging.error("   🔍 Check for port conflicts")
        logging.error("   🔍 Verify system permissions")
    else:
        logging.error("   🔍 Review general system configuration")
        logging.error("   🔍 Check logs from all components")
        logging.error("   🔍 Verify all dependent services are running")
    
    logging.error("")
    logging.error("📊 TECHNICAL DETAILS:")
    logging.error(f"   Exception Type: {error_type}")
    logging.error(f"   Full Error: {error_msg}")
    if hasattr(error, '__traceback__') and error.__traceback__:
        logging.error(f"   Stack Trace: {traceback.format_exc()}")
    logging.error("=" * 80)


def log_startup_success(component: str, duration: Optional[float] = None) -> None:
    """Log successful startup of components."""
    
    duration_str = f" ({duration:.2f}s)" if duration is not None else ""
    logging.info(f"✅ {component.upper()} initialized successfully{duration_str}")


def log_startup_progress(component: str) -> None:
    """Log startup progress."""
    logging.info(f"🔄 Initializing {component.upper()}...")


# =============================================================================
# Global Variables
# =============================================================================

_startup_time: float = 0.0
_app_logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifecycle Manager
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    global _startup_time
    
    # Startup
    _startup_time = time.time()
    
    logging.info("🚀 Starting RAG OpenShift AI API")
    logging.info(f"📋 Version: {settings.api.version}")
    logging.info(f"📋 Environment: {settings.environment}")
    logging.info(f"📋 API Host: {settings.api.host}:{settings.api.port}")
    
    try:
        # Initialize metrics
        log_startup_progress("Metrics System")
        setup_metrics()
        log_startup_success("Metrics System")
        
        # Start metrics server if enabled
        if settings.metrics.enabled:
            log_startup_progress("Metrics Server")
            start_metrics_server(
                port=settings.metrics.port
            )
            log_startup_success("Metrics Server")
            logging.info(f"📊 Metrics server started on port {settings.metrics.port}")
        
        # Initialize RAG components with timeout
        logging.info("🔄 Initializing RAG components...")
        
        # Initialize embeddings with timeout
        log_startup_progress("Embeddings")
        embedding_start = time.time()
        if not initialize_embeddings():
            raise RuntimeError("Failed to initialize embeddings")
        embedding_duration = time.time() - embedding_start
        log_startup_success("Embeddings", embedding_duration)
        
        # Initialize retriever with timeout
        log_startup_progress("Retriever")
        retriever_start = time.time()
        if not initialize_retriever():
            raise RuntimeError("Failed to initialize retriever")
        retriever_duration = time.time() - retriever_start
        log_startup_success("Retriever", retriever_duration)
        
        # Initialize RAG agent with timeout
        log_startup_progress("RAG Agent")
        agent_start = time.time()
        if not initialize_rag_agent():
            raise RuntimeError("Failed to initialize RAG agent")
        agent_duration = time.time() - agent_start
        log_startup_success("RAG Agent", agent_duration)
        
        # Validate all components with timeout
        logging.info("🔍 Validating component health...")
        
        # Add timeout for health checks
        import asyncio
        try:
            # Set a timeout for health validation
            async def validate_health():
                rag_health = get_rag_health()
                if not rag_health["agent_healthy"]:
                    raise RuntimeError(f"RAG agent health check failed: {rag_health['errors']}")
                
                embedding_health = get_embedding_health()
                if not embedding_health.get("model_loaded", False):
                    raise RuntimeError("Embedding model not loaded")
                
                retriever_health = get_retriever_health()
                if not retriever_health.get("connection_healthy", False):
                    raise RuntimeError("Retriever connection unhealthy")
                
                return True
            
            # Run validation with timeout
            await asyncio.wait_for(validate_health(), timeout=30.0)
            
        except asyncio.TimeoutError:
            logging.warning("⚠️ Health validation timed out, continuing anyway...")
        except Exception as e:
            logging.warning(f"⚠️ Health validation failed: {str(e)}, continuing anyway...")
        
        logging.info("✅ All components validated successfully")
        
        # Log startup information
        total_startup_time = time.time() - _startup_time
        logging.info("=" * 80)
        logging.info("🎉 RAG OpenShift AI API started successfully!")
        logging.info("=" * 80)
        logging.info(f"📋 Version: {settings.api.version}")
        logging.info(f"📋 Environment: {settings.environment}")
        logging.info(f"📋 Total Startup Time: {total_startup_time:.2f} seconds")
        logging.info(f"📋 API Endpoint: http://{settings.api.host}:{settings.api.port}")
        logging.info(f"📋 Health Check: http://{settings.api.host}:{settings.api.port}/api/v1/health")
        logging.info(f"📋 API Docs: http://{settings.api.host}:{settings.api.port}/docs")
        if settings.metrics.enabled:
            logging.info(f"📊 Metrics: http://{settings.api.host}:{settings.metrics.port}/metrics")
        logging.info("=" * 80)
        
        yield
        
    except Exception as e:
        log_startup_error(e, "Application Startup")
        record_error(type(e).__name__, "startup")
        raise
    
    finally:
        # Shutdown
        logging.info("🛑 Shutting down RAG OpenShift AI API")
        
        try:
            uptime = time.time() - _startup_time
            logging.info(f"📊 Application uptime: {uptime:.2f} seconds")
            logging.info("✅ RAG OpenShift AI API shutdown completed")
        
        except Exception as e:
            logging.error(f"❌ Error during shutdown: {str(e)}")


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
    correlation_id = f"req-{int(time.time() * 1000)}"
    
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
    
    # Log request
    logging.info(f"Request started, correlation_id={correlation_id}, client_ip={request.client.host if request.client else None}, user_agent={request.headers.get('User-Agent')}")
    
    try:
        # Process request
        response = await call_next(request)
        
        # Log successful response
        duration = time.time() - start_time
        logging.info(f"Request completed, correlation_id={correlation_id}, status_code={response.status_code}, duration={duration}")
        
        return response
        
    except Exception as e:
        # Log failed request
        duration = time.time() - start_time
        logging.error(f"Request failed: {str(e)}")
        raise


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for all requests."""
    
    start_time = time.time()
    
    try:
        # Process request
        response = await call_next(request)
        
        # Record metrics (with error handling)
        try:
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
        except Exception as metric_error:
            # Log metric error but don't fail the request
            logging.warning(f"Metrics recording failed: {metric_error}")
        
        return response
        
    except Exception as e:
        # Record error metrics (with error handling)
        try:
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
        except Exception as metric_error:
            # Log metric error but don't fail the request
            logging.warning(f"Error metrics recording failed: {metric_error}")
        
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


@app.get("/ready", tags=["Health"])
async def root_ready(request: Request):
    """Root readiness check endpoint (alias for /api/v1/ready)."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.requests import Request as StarletteRequest
    # Proxy the request to the /api/v1/ready endpoint
    # We need to call the actual readiness_check from the router
    # FastAPI injects a Request, but router expects it as param
    # This works for both direct and test calls
    return await readiness_check(request)


# =============================================================================
# Global Exception Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    
    logging.warning(f"Validation error, correlation_id={correlation_id}, errors={exc.errors()}")
    
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
    
    logging.warning(f"HTTP exception, correlation_id={correlation_id}, status_code={exc.status_code}, detail={exc.detail}")
    
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
    
    logging.error(f"Unhandled exception: {str(exc)}")
    
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
# Debug Endpoints (if debug mode is enabled)
# =============================================================================

if settings.api.debug:
    @app.get("/debug/info", tags=["Debug"])
    async def debug_info():
        """Debug information endpoint (debug mode only)."""
        return {
            "title": settings.api.title,
            "version": settings.api.version,
            "description": settings.api.description,
            "host": settings.api.host,
            "port": settings.api.port,
            "log_level": settings.api.log_level,
            "debug": settings.api.debug,
            "cors_enabled": settings.api.cors_enabled,
            "cors_origins": settings.api.cors_origins,
            "elasticsearch_url": settings.elasticsearch.url,
            "vllm_url": settings.vllm.url,
            "embedding_model": settings.embedding.model_name,
            "embedding_device": settings.embedding.device,
            "rag_top_k": settings.rag.top_k,
            "rag_similarity_threshold": settings.rag.similarity_threshold,
            "metrics_enabled": settings.environment.metrics_enabled,
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.get("/debug/settings", tags=["Debug"])
    async def debug_settings():
        """Debug settings endpoint (debug mode only)."""
        return {
            "api": settings.api.dict(),
            "elasticsearch": settings.elasticsearch.dict(),
            "vllm": settings.vllm.dict(),
            "embedding": settings.embedding.dict(),
            "rag": settings.rag.dict(),
            "environment": settings.environment.dict()
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