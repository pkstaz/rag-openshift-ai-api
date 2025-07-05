import time
from typing import Dict, Any, List
from contextlib import asynccontextmanager
import logging

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .models import (
    QueryRequest, QueryResponse, ErrorResponse,
    SimpleHealthResponse as HealthResponse, InfoResponse, ModelInfo
)
from ..config.settings import settings
from ..utils.metrics import (
    increment_request_counter, record_request_duration,
    record_error, get_metrics_summary
)
from ..rag import get_rag_health, get_embedding_health, get_retriever_health


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(tags=["RAG API"])


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
    logging.info("=" * 60)
    logging.info("📥 REQUEST RECEIVED")
    logging.info("=" * 60)
    logging.info(f"📋 Method: {request.method}")
    logging.info(f"📋 URL: {request.url}")
    logging.info(f"📋 Correlation ID: {correlation_id}")
    logging.info(f"📋 Client IP: {request.client.host if request.client else None}")
    logging.info(f"📋 User-Agent: {request.headers.get('User-Agent')}")
    logging.info("=" * 60)
    
    try:
        yield correlation_id, start_time
    except Exception as e:
        # Log error
        logging.error("=" * 80)
        logging.error("🚨 REQUEST PROCESSING ERROR")
        logging.error("=" * 80)
        logging.error(f"📋 Correlation ID: {correlation_id}")
        logging.error(f"📋 Error Type: {type(e).__name__}")
        logging.error(f"📋 Error Message: {str(e)}")
        logging.error("=" * 80)
        record_error(type(e).__name__, "api")
        raise
    finally:
        # Log response
        duration = time.time() - start_time
        logging.info("=" * 60)
        logging.info("📤 REQUEST PROCESSED")
        logging.info("=" * 60)
        logging.info(f"📋 Method: {request.method}")
        logging.info(f"📋 URL: {request.url}")
        logging.info(f"📋 Duration: {duration} seconds")
        logging.info(f"📋 Correlation ID: {correlation_id}")
        logging.info("=" * 60)


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
            increment_request_counter("POST", "/query", "200")
            
            logging.info("=" * 60)
            logging.info("🔄 PROCESSING QUERY REQUEST")
            logging.info("=" * 60)
            logging.info(f"📋 Correlation ID: {correlation_id}")
            logging.info(f"📋 Question Length: {len(query_request.question)}")
            logging.info(f"📋 LLM Params: {query_request.llm_params}")
            logging.info(f"📋 Retrieval Params: {query_request.retrieval_params}")
            logging.info("=" * 60)
            
            # Get RAG agent
            from ..rag.agent import get_rag_agent
            rag_agent = get_rag_agent()
            
            # Process query
            response = rag_agent.answer_query(
                question=query_request.question,
                llm_params=query_request.llm_params,
                retrieval_params=query_request.retrieval_params
            )
            
            # Record request duration
            duration = time.time() - start_time
            record_request_duration("POST", "/query", "200", duration)
            
            logging.info("=" * 60)
            logging.info("✅ QUERY PROCESSED SUCCESSFULLY")
            logging.info("=" * 60)
            logging.info(f"📋 Correlation ID: {correlation_id}")
            logging.info(f"📋 Answer Length: {len(response.answer)}")
            logging.info(f"📋 Num Sources: {len(response.sources)}")
            logging.info(f"📋 Confidence Score: {response.confidence_score}")
            logging.info(f"📋 Processing Time: {response.query_metadata.processing_time_ms if response.query_metadata else None} ms")
            logging.info("=" * 60)
            
            return response
            
        except ValueError as e:
            # Bad request - validation error
            increment_request_counter("POST", "/query", "400")
            record_error("ValueError", "api")
            
            logging.warning("=" * 60)
            logging.warning("⚠️ INVALID QUERY REQUEST")
            logging.warning("=" * 60)
            logging.warning(f"📋 Correlation ID: {correlation_id}")
            logging.warning(f"📋 Error: {str(e)}")
            logging.warning("=" * 60)
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request: {str(e)}"
            )
            
        except ConnectionError as e:
            # Service unavailable - connection issues
            increment_request_counter("POST", "/query", "503")
            record_error("ConnectionError", "api")
            
            logging.error("=" * 80)
            logging.error("🚨 SERVICE UNAVAILABLE")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )
            
        except Exception as e:
            # Internal server error
            increment_request_counter("POST", "/query", "500")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 INTERNAL SERVER ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error("=" * 80)
            
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
        
        increment_request_counter("GET", "/health", "200")
        
        try:
            # Basic health check - just check if API is responding
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "version": settings.api.version,
                "service": "rag-api"
            }
            
            duration = time.time() - start_time
            record_request_duration("GET", "/health", "200", duration)
            
            logging.debug("=" * 50)
            logging.debug("✅ HEALTH CHECK COMPLETED")
            logging.debug("=" * 50)
            logging.debug(f"📋 Correlation ID: {correlation_id}")
            logging.debug(f"📋 Status: healthy")
            logging.debug("=" * 50)
            
            return HealthResponse(**health_status)
            
        except Exception as e:
            increment_request_counter("GET", "/health", "503")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 HEALTH CHECK FAILED")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
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
            # Fast readiness check - only check basic connectivity
            components_status = {}
            errors = []
            
            # Check Elasticsearch (fast)
            try:
                from ..rag.retriever import get_retriever_health
                es_health = get_retriever_health()
                components_status["elasticsearch"] = es_health
                if not es_health.get("connection_healthy", False):
                    errors.append("Elasticsearch connection unhealthy")
            except Exception as e:
                components_status["elasticsearch"] = {"connection_healthy": False, "error": str(e)}
                errors.append(f"Elasticsearch check failed: {str(e)}")
            
            # Check Embeddings (fast)
            try:
                from ..rag.embeddings import get_embedding_health
                emb_health = get_embedding_health()
                components_status["embeddings"] = emb_health
                if not emb_health.get("model_loaded", False):
                    errors.append("Embedding model not loaded")
            except Exception as e:
                components_status["embeddings"] = {"model_loaded": False, "error": str(e)}
                errors.append(f"Embedding check failed: {str(e)}")
            
            # Check vLLM (fast - just client existence)
            try:
                from ..rag.agent import get_rag_agent
                agent = get_rag_agent()
                if hasattr(agent, 'llm_client') and agent.llm_client is not None:
                    components_status["vllm"] = {
                        "connection_healthy": True,
                        "model_name": agent.model_name
                    }
                else:
                    components_status["vllm"] = {"connection_healthy": False, "error": "LLM client not initialized"}
                    errors.append("vLLM client not initialized")
            except Exception as e:
                components_status["vllm"] = {"connection_healthy": False, "error": str(e)}
                errors.append(f"vLLM check failed: {str(e)}")
            
            # Determine overall health
            agent_healthy = len(errors) == 0
            
            if not agent_healthy:
                increment_request_counter("GET", "/ready", "503")
                record_error("UnhealthyDependencies", "api")
                
                logging.warning("=" * 80)
                logging.warning("⚠️ READINESS CHECK FAILED")
                logging.warning("=" * 80)
                logging.warning(f"📋 Correlation ID: {correlation_id}")
                logging.warning(f"📋 Errors: {errors}")
                logging.warning("=" * 80)
                
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "not_ready",
                        "errors": errors,
                        "components": components_status
                    }
                )
            
            # All dependencies healthy
            increment_request_counter("GET", "/ready", "200")
            
            health_status = {
                "status": "ready",
                "timestamp": time.time(),
                "version": settings.api.version,
                "service": "rag-api",
                "components": components_status,
                "performance": {
                    "total_queries_processed": 0,
                    "total_processing_time": 0.0,
                    "average_processing_time": 0.0
                }
            }
            
            duration = time.time() - start_time
            record_request_duration("GET", "/ready", "200", duration)
            
            logging.info("=" * 60)
            logging.info("✅ READINESS CHECK PASSED")
            logging.info("=" * 60)
            logging.info(f"📋 Correlation ID: {correlation_id}")
            logging.info(f"📋 Components: {list(components_status.keys())}")
            logging.info(f"📋 Duration: {duration:.3f}s")
            logging.info("=" * 60)
            
            return HealthResponse(**health_status)
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            increment_request_counter("GET", "/ready", "503")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 READINESS CHECK ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
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
        
        increment_request_counter("GET", "/metrics", "200")
        
        try:
            # Generate Prometheus metrics
            metrics_data = generate_latest()
            
            duration = time.time() - start_time
            record_request_duration("GET", "/metrics", "200", duration)
            
            logging.debug("=" * 50)
            logging.debug("📊 METRICS REQUESTED")
            logging.debug("=" * 50)
            logging.debug(f"📋 Correlation ID: {correlation_id}")
            logging.debug(f"📋 Metrics Size: {len(metrics_data)}")
            logging.debug("=" * 50)
            
            return PlainTextResponse(
                content=metrics_data,
                media_type=CONTENT_TYPE_LATEST
            )
            
        except Exception as e:
            increment_request_counter("GET", "/metrics", "500")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 METRICS GENERATION FAILED")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
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
        
        increment_request_counter("GET", "/info", "200")
        
        try:
            # Get RAG agent info
            from ..rag.agent import get_rag_info
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
            record_request_duration("GET", "/info", "200", duration)
            
            logging.info("=" * 50)
            logging.info("ℹ️ API INFO REQUESTED")
            logging.info("=" * 50)
            logging.info(f"📋 Correlation ID: {correlation_id}")
            logging.info(f"📋 Version: {settings.api.version}")
            logging.info("=" * 50)
            
            return InfoResponse(**info_data)
            
        except Exception as e:
            increment_request_counter("GET", "/info", "500")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 API INFO FAILED")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
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
        
        increment_request_counter("GET", "/models", "200")
        
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
            record_request_duration("GET", "/models", "200", duration)
            
            logging.info("=" * 50)
            logging.info("🤖 MODELS LIST REQUESTED")
            logging.info("=" * 50)
            logging.info(f"📋 Correlation ID: {correlation_id}")
            logging.info(f"📋 Num Models: {len(models)}")
            logging.info("=" * 50)
            
            return models
            
        except Exception as e:
            increment_request_counter("GET", "/models", "500")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 MODELS LIST FAILED")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve models information"
            )


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
        
        increment_request_counter("GET", "/status", "200")
        
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
            record_request_duration("GET", "/status", "200", duration)
            
            logging.info("=" * 50)
            logging.info("📊 DETAILED STATUS REQUESTED")
            logging.info("=" * 50)
            logging.info(f"📋 Correlation ID: {correlation_id}")
            logging.info("=" * 50)
            
            return status_data
            
        except Exception as e:
            increment_request_counter("GET", "/status", "500")
            record_error(type(e).__name__, "api")
            
            logging.error("=" * 80)
            logging.error("🚨 DETAILED STATUS FAILED")
            logging.error("=" * 80)
            logging.error(f"📋 Correlation ID: {correlation_id}")
            logging.error(f"📋 Error: {str(e)}")
            logging.error("=" * 80)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve status information"
            ) 