"""
Utilities Package

This package contains utility functions and helpers for:
- Logging and observability
- Data processing and validation
- Common operations and helpers
"""

from .logging import (
    setup_logging,
    get_logger,
    log_request,
    log_rag_operation,
    log_performance,
    log_error,
    log_openshift_event,
    sanitize_log_data,
    get_correlation_id,
    log_startup_info,
    log_shutdown_info,
)

from .metrics import (
    setup_metrics,
    get_metrics,
    track_api_request,
    track_rag_query,
    track_elasticsearch_search,
    track_vllm_generation,
    track_embedding_generation,
    increment_llm_tokens,
    record_chunks_retrieved,
    update_elasticsearch_status,
    update_vllm_status,
    record_error,
    record_elasticsearch_error,
    record_vllm_error,
    update_component_health,
    get_metrics_summary,
)

__all__ = [
    "setup_logging",
    "get_logger", 
    "log_request",
    "log_rag_operation",
    "log_performance",
    "log_error",
    "log_openshift_event",
    "sanitize_log_data",
    "get_correlation_id",
    "log_startup_info",
    "log_shutdown_info",
    "setup_metrics",
    "get_metrics",
    "track_api_request",
    "track_rag_query",
    "track_elasticsearch_search",
    "track_vllm_generation",
    "track_embedding_generation",
    "increment_llm_tokens",
    "record_chunks_retrieved",
    "update_elasticsearch_status",
    "update_vllm_status",
    "record_error",
    "record_elasticsearch_error",
    "record_vllm_error",
    "update_component_health",
    "get_metrics_summary",
] 