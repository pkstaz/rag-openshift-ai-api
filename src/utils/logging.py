import logging
import time
import uuid
import json
import traceback
import asyncio
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone

import structlog
from structlog.stdlib import LoggerFactory


# =============================================================================
# Structured Logging Configuration
# =============================================================================

def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for OpenShift compatibility."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add timestamp
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON renderer for OpenShift compatibility
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        force=True
    )


def get_logger(component_name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for a specific component."""
    return structlog.get_logger(component_name)


# =============================================================================
# Context Processors for Automatic Metadata
# =============================================================================

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to all log entries."""
    if not event_dict.get("correlation_id"):
        event_dict["correlation_id"] = str(uuid.uuid4())
    return event_dict


def add_component_info(logger, method_name, event_dict):
    """Add component information to log entries."""
    event_dict["component"] = "rag-api"
    event_dict["service"] = "rag-openshift-ai-api"
    return event_dict


def add_timestamp(logger, method_name, event_dict):
    """Add ISO timestamp to log entries."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


# =============================================================================
# Request Logging Utilities
# =============================================================================

def log_request(
    operation: str,
    request_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """Decorator for logging HTTP requests with performance metrics."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = request_id or str(uuid.uuid4())
            
            logger = get_logger("api.request")
            
            # Log request start
            logger.info(
                "Request started",
                operation=operation,
                correlation_id=correlation_id,
                request_id=request_id,
                **(additional_context or {})
            )
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful request
                logger.info(
                    "Request completed",
                    operation=operation,
                    correlation_id=correlation_id,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    status="success",
                    **(additional_context or {})
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log failed request
                logger.error(
                    "Request failed",
                    operation=operation,
                    correlation_id=correlation_id,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    **(additional_context or {})
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = request_id or str(uuid.uuid4())
            
            logger = get_logger("api.request")
            
            # Log request start
            logger.info(
                "Request started",
                operation=operation,
                correlation_id=correlation_id,
                request_id=request_id,
                **(additional_context or {})
            )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful request
                logger.info(
                    "Request completed",
                    operation=operation,
                    correlation_id=correlation_id,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    status="success",
                    **(additional_context or {})
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log failed request
                logger.error(
                    "Request failed",
                    operation=operation,
                    correlation_id=correlation_id,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    **(additional_context or {})
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_rag_operation(
    operation: str,
    correlation_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """Decorator for logging RAG operations with detailed metrics."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            op_correlation_id = correlation_id or str(uuid.uuid4())
            
            logger = get_logger("rag.operation")
            
            # Log operation start
            logger.info(
                "RAG operation started",
                operation=operation,
                correlation_id=op_correlation_id,
                **(additional_context or {})
            )
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful operation
                logger.info(
                    "RAG operation completed",
                    operation=operation,
                    correlation_id=op_correlation_id,
                    duration_ms=duration_ms,
                    status="success",
                    **(additional_context or {})
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log failed operation
                logger.error(
                    "RAG operation failed",
                    operation=operation,
                    correlation_id=op_correlation_id,
                    duration_ms=duration_ms,
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    **(additional_context or {})
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            op_correlation_id = correlation_id or str(uuid.uuid4())
            
            logger = get_logger("rag.operation")
            
            # Log operation start
            logger.info(
                "RAG operation started",
                operation=operation,
                correlation_id=op_correlation_id,
                **(additional_context or {})
            )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful operation
                logger.info(
                    "RAG operation completed",
                    operation=operation,
                    correlation_id=op_correlation_id,
                    duration_ms=duration_ms,
                    status="success",
                    **(additional_context or {})
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log failed operation
                logger.error(
                    "RAG operation failed",
                    operation=operation,
                    correlation_id=op_correlation_id,
                    duration_ms=duration_ms,
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    **(additional_context or {})
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# =============================================================================
# Performance Timing Utilities
# =============================================================================

@contextmanager
def log_performance(
    operation: str,
    logger_name: str = "performance",
    additional_context: Optional[Dict[str, Any]] = None
):
    """Context manager for logging performance metrics."""
    
    start_time = time.time()
    correlation_id = str(uuid.uuid4())
    logger = get_logger(logger_name)
    
    # Log operation start
    logger.info(
        "Performance operation started",
        operation=operation,
        correlation_id=correlation_id,
        **(additional_context or {})
    )
    
    try:
        yield correlation_id
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log successful operation
        logger.info(
            "Performance operation completed",
            operation=operation,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            status="success",
            **(additional_context or {})
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log failed operation
        logger.error(
            "Performance operation failed",
            operation=operation,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            status="error",
            error_type=type(e).__name__,
            error_message=str(e),
            **(additional_context or {})
        )
        raise


def log_error(
    error: Exception,
    operation: str,
    correlation_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log errors with full context and stack trace."""
    
    logger = get_logger("error")
    error_correlation_id = correlation_id or str(uuid.uuid4())
    
    logger.error(
        "Error occurred",
        operation=operation,
        correlation_id=error_correlation_id,
        error_type=type(error).__name__,
        error_message=str(error),
        stack_trace=traceback.format_exc(),
        **(additional_context or {})
    )


# =============================================================================
# OpenShift-specific Logging
# =============================================================================

def log_openshift_event(
    event_type: str,
    event_message: str,
    correlation_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log events in OpenShift-compatible format."""
    
    logger = get_logger("openshift.event")
    event_correlation_id = correlation_id or str(uuid.uuid4())
    
    logger.info(
        "OpenShift event",
        event_type=event_type,
        event_message=event_message,
        correlation_id=event_correlation_id,
        platform="openshift",
        **(additional_context or {})
    )


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from log data."""
    
    sensitive_fields = {
        'password', 'token', 'secret', 'key', 'credential',
        'authorization', 'cookie', 'session'
    }
    
    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


# =============================================================================
# Convenience Functions
# =============================================================================

def get_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def log_startup_info() -> None:
    """Log application startup information."""
    logger = get_logger("startup")
    logger.info(
        "Application starting",
        version="0.1.0",
        environment="development",
        platform="openshift"
    )


def log_shutdown_info() -> None:
    """Log application shutdown information."""
    logger = get_logger("shutdown")
    logger.info(
        "Application shutting down",
        version="0.1.0",
        platform="openshift"
    )


# =============================================================================
# Simple Logging Functions for API Routes
# =============================================================================

def log_http_request(
    method: str,
    url: str,
    correlation_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log HTTP request details."""
    logger = get_logger("api.request")
    logger.info(
        "HTTP request received",
        method=method,
        url=url,
        correlation_id=correlation_id,
        client_ip=client_ip,
        user_agent=user_agent
    )


def log_http_response(
    method: str,
    url: str,
    duration: float,
    correlation_id: Optional[str] = None,
    status_code: Optional[int] = None
) -> None:
    """Log HTTP response details."""
    logger = get_logger("api.response")
    logger.info(
        "HTTP response sent",
        method=method,
        url=url,
        duration=duration,
        correlation_id=correlation_id,
        status_code=status_code
    )


# Default logging configuration
DEFAULT_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        }
    }
} 