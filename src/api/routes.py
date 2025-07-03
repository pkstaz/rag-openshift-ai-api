import time
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .models import (
    QueryRequest, QueryResponse, ErrorResponse,
    SimpleHealthResponse as HealthResponse, InfoResponse, ModelInfo
)
from ..config.settings import settings
from ..utils.logging import get_logger, log_http_request, log_http_response
from ..utils.metrics import (
    increment_request_counter, record_request_duration,
    record_error, get_metrics_summary
)
from ..rag.agent import get_rag_agent, get_rag_health, get_rag_info
from ..rag.embeddings import get_embedding_health
from ..rag.retriever import get_retriever_health


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(prefix="/api/v1", tags=["RAG API"])

logger = get_logger("api.routes")


# =============================================================================
# Middleware Functions
# =============================================================================

def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-ID", f"req-{int(time.time() * 1000)}")


@asynccontextmanager
async def request_context(request: Request):
    """Context manager for request processing with logging and metrics."""
    start_time = time.time()
    correlation_id = get_correlation_id(request)
    
    # Log request start
    log_http_request(
        request.method,
        str(request.url),
        correlation_id=correlation_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    try:
        yield correlation_id, start_time
    except Exception as e:
        # Log error
        logger.error(
            "Request processing error",
            correlation_id=correlation_id,
            error=str(e),
            error_type=type(e).__name__
        )
        record_error(type(e).__name__, "api")
        raise
    finally:
        # Log response
        duration = time.time() - start_time
        log_http_response(
            request.method,
            str(request.url),
            duration,
            correlation_id=correlation_id
        )


# =============================================================================
# Query Endpoint
# =============================================================================

@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Process a query using RAG pipeline",
    description="Submit a question to be answered using the RAG (Retrieval-Augmented Generation) pipeline"
)
async def process_query(
    request: Request,
    query_request: QueryRequest
) -> QueryResponse:
    """Process a query using the RAG pipeline."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        try:
            # Increment request counter
            increment_request_counter("POST", "/api/v1/query", "200")
            
            logger.info(
                "Processing query request",
                correlation_id=correlation_id,
                question_length=len(query_request.question),
                llm_params=query_request.llm_params,
                retrieval_params=query_request.retrieval_params
            )
            
            # Get RAG agent
            rag_agent = get_rag_agent()
            
            # Process query
            response = rag_agent.answer_query(
                question=query_request.question,
                llm_params=query_request.llm_params,
                retrieval_params=query_request.retrieval_params
            )
            
            # Record request duration
            duration = time.time() - start_time
            record_request_duration("POST", "/api/v1/query", "200", duration)
            
            logger.info(
                "Query processed successfully",
                correlation_id=correlation_id,
                answer_length=len(response.answer),
                num_sources=len(response.sources),
                confidence_score=response.confidence_score,
                processing_time_ms=response.query_metadata.processing_time_ms if response.query_metadata else None
            )
            
            return response
            
        except ValueError as e:
            # Bad request - validation error
            increment_request_counter("POST", "/api/v1/query", "400")
            record_error("ValueError", "api")
            
            logger.warning(
                "Invalid query request",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request: {str(e)}"
            )
            
        except ConnectionError as e:
            # Service unavailable - connection issues
            increment_request_counter("POST", "/api/v1/query", "503")
            record_error("ConnectionError", "api")
            
            logger.error(
                "Service unavailable",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )
            
        except Exception as e:
            # Internal server error
            increment_request_counter("POST", "/api/v1/query", "500")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Internal server error during query processing",
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while processing your request."
            )


# =============================================================================
# Health Check Endpoints
# =============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Check if the API is running and responding"
)
async def health_check(request: Request) -> HealthResponse:
    """Basic health check endpoint."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        increment_request_counter("GET", "/api/v1/health", "200")
        
        try:
            # Basic health check - just check if API is responding
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "version": settings.api.version,
                "service": "rag-api"
            }
            
            duration = time.time() - start_time
            record_request_duration("GET", "/api/v1/health", "200", duration)
            
            logger.debug(
                "Health check completed",
                correlation_id=correlation_id,
                status="healthy"
            )
            
            return HealthResponse(**health_status)
            
        except Exception as e:
            increment_request_counter("GET", "/api/v1/health", "503")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Health check failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unhealthy"
            )


@router.get(
    "/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if all dependencies (ElasticSearch, vLLM) are available"
)
async def readiness_check(request: Request) -> HealthResponse:
    """Readiness check endpoint - verifies all dependencies."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        try:
            # Check RAG agent health
            rag_health = get_rag_health()
            
            if not rag_health["agent_healthy"]:
                increment_request_counter("GET", "/api/v1/ready", "503")
                record_error("UnhealthyDependencies", "api")
                
                logger.warning(
                    "Readiness check failed - unhealthy dependencies",
                    correlation_id=correlation_id,
                    errors=rag_health["errors"]
                )
                
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "not_ready",
                        "errors": rag_health["errors"],
                        "components": rag_health["components"]
                    }
                )
            
            # All dependencies healthy
            increment_request_counter("GET", "/api/v1/ready", "200")
            
            health_status = {
                "status": "ready",
                "timestamp": time.time(),
                "version": settings.api.version,
                "service": "rag-api",
                "components": rag_health["components"],
                "performance": rag_health["performance"]
            }
            
            duration = time.time() - start_time
            record_request_duration("GET", "/api/v1/ready", "200", duration)
            
            logger.info(
                "Readiness check passed",
                correlation_id=correlation_id,
                components=list(rag_health["components"].keys())
            )
            
            return HealthResponse(**health_status)
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            increment_request_counter("GET", "/api/v1/ready", "503")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Readiness check error",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )


# =============================================================================
# Metrics Endpoint
# =============================================================================

@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Prometheus metrics",
    description="Get Prometheus metrics for monitoring and alerting"
)
async def get_metrics(request: Request) -> PlainTextResponse:
    """Get Prometheus metrics."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        increment_request_counter("GET", "/api/v1/metrics", "200")
        
        try:
            # Generate Prometheus metrics
            metrics_data = generate_latest()
            
            duration = time.time() - start_time
            record_request_duration("GET", "/api/v1/metrics", "200", duration)
            
            logger.debug(
                "Metrics requested",
                correlation_id=correlation_id,
                metrics_size=len(metrics_data)
            )
            
            return PlainTextResponse(
                content=metrics_data,
                media_type=CONTENT_TYPE_LATEST
            )
            
        except Exception as e:
            increment_request_counter("GET", "/api/v1/metrics", "500")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Metrics generation failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate metrics"
            )


# =============================================================================
# Info Endpoints
# =============================================================================

@router.get(
    "/info",
    response_model=InfoResponse,
    status_code=status.HTTP_200_OK,
    summary="API information",
    description="Get information about the API including version and build details"
)
async def get_api_info(request: Request) -> InfoResponse:
    """Get API information."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        increment_request_counter("GET", "/api/v1/info", "200")
        
        try:
            # Get RAG agent info
            rag_info = get_rag_info()
            
            info_data = {
                "name": "RAG OpenShift AI API",
                "version": settings.api.version,
                "description": "Retrieval-Augmented Generation API for OpenShift",
                "build_date": settings.api.build_date,
                "git_commit": settings.api.git_commit,
                "environment": settings.environment,
                "rag_agent": rag_info,
                "settings": {
                    "api_host": settings.api.host,
                    "api_port": settings.api.port,
                    "elasticsearch_url": settings.elasticsearch.url,
                    "vllm_url": settings.vllm.url,
                    "embedding_model": settings.embeddings.model_name,
                    "rag_top_k": settings.rag.top_k,
                    "rag_search_type": settings.rag.search_type
                }
            }
            
            duration = time.time() - start_time
            record_request_duration("GET", "/api/v1/info", "200", duration)
            
            logger.info(
                "API info requested",
                correlation_id=correlation_id,
                version=settings.api.version
            )
            
            return InfoResponse(**info_data)
            
        except Exception as e:
            increment_request_counter("GET", "/api/v1/info", "500")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Failed to get API info",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve API information"
            )


@router.get(
    "/models",
    response_model=List[ModelInfo],
    status_code=status.HTTP_200_OK,
    summary="Available models",
    description="Get list of available models in vLLM"
)
async def get_available_models(request: Request) -> List[ModelInfo]:
    """Get list of available models in vLLM."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        increment_request_counter("GET", "/api/v1/models", "200")
        
        try:
            # For now, return the configured model
            # In a real implementation, you might query vLLM for available models
            models = [
                ModelInfo(
                    name=settings.vllm.model_name,
                    type="llm",
                    provider="vllm",
                    url=settings.vllm.url,
                    parameters={
                        "temperature": settings.vllm.temperature,
                        "max_tokens": settings.vllm.max_tokens,
                        "top_p": settings.vllm.top_p,
                        "top_k": settings.vllm.top_k
                    }
                )
            ]
            
            # Add embedding model
            models.append(
                ModelInfo(
                    name=settings.embeddings.model_name,
                    type="embedding",
                    provider="sentence-transformers",
                    url="local",
                    parameters={
                        "device": settings.embeddings.device,
                        "max_length": settings.embeddings.max_length
                    }
                )
            )
            
            duration = time.time() - start_time
            record_request_duration("GET", "/api/v1/models", "200", duration)
            
            logger.info(
                "Models list requested",
                correlation_id=correlation_id,
                num_models=len(models)
            )
            
            return models
            
        except Exception as e:
            increment_request_counter("GET", "/api/v1/models", "500")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Failed to get models list",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve models information"
            )


# =============================================================================
# Error Handlers
# =============================================================================

@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured error responses."""
    
    correlation_id = get_correlation_id(request)
    
    error_response = ErrorResponse(
        error=exc.detail,
        status_code=exc.status_code,
        timestamp=time.time(),
        correlation_id=correlation_id
    )
    
    logger.warning(
        "HTTP exception",
        correlation_id=correlation_id,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return error_response


@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured error responses."""
    
    correlation_id = get_correlation_id(request)
    
    error_response = ErrorResponse(
        error="Internal server error",
        status_code=500,
        timestamp=time.time(),
        correlation_id=correlation_id
    )
    
    logger.error(
        "Unhandled exception",
        correlation_id=correlation_id,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    record_error(type(exc).__name__, "api")
    
    return error_response


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get(
    "/status",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Detailed status",
    description="Get detailed status of all components"
)
async def get_detailed_status(request: Request) -> Dict[str, Any]:
    """Get detailed status of all components."""
    
    async with request_context(request) as (correlation_id, start_time):
        
        increment_request_counter("GET", "/api/v1/status", "200")
        
        try:
            # Collect status from all components
            status_data = {
                "api": {
                    "status": "healthy",
                    "version": settings.api.version,
                    "timestamp": time.time()
                },
                "rag_agent": get_rag_health(),
                "embeddings": get_embedding_health(),
                "retriever": get_retriever_health(),
                "metrics": get_metrics_summary()
            }
            
            duration = time.time() - start_time
            record_request_duration("GET", "/api/v1/status", "200", duration)
            
            logger.info(
                "Detailed status requested",
                correlation_id=correlation_id
            )
            
            return status_data
            
        except Exception as e:
            increment_request_counter("GET", "/api/v1/status", "500")
            record_error(type(e).__name__, "api")
            
            logger.error(
                "Failed to get detailed status",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve status information"
            ) 