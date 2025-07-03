"""
RAG (Retrieval-Augmented Generation) Package

This package contains the core RAG implementation including:
- Document processing and embedding
- Vector search and retrieval
- LLM integration and response generation
"""

from .agent import (
    RAGAgent,
    get_rag_agent,
    initialize_rag_agent,
    answer_query,
    get_rag_health,
    get_rag_info,
    ProcessingMetrics
)
from .embeddings import (
    EmbeddingManager,
    get_embedding_manager,
    initialize_embeddings,
    cleanup_embeddings,
    embed_query,
    embed_batch,
    compute_similarity,
    validate_embedding_consistency,
    get_embedding_health,
)

from .retriever import (
    ElasticSearchRetriever,
    SearchResult,
    SearchParams,
    get_retriever,
    initialize_retriever,
    search_documents,
    get_retriever_health,
    validate_retriever_index,
)

__all__ = [
    "RAGAgent", 
    "EmbeddingManager",
    "get_embedding_manager",
    "initialize_embeddings",
    "cleanup_embeddings",
    "embed_query",
    "embed_batch",
    "compute_similarity",
    "validate_embedding_consistency",
    "get_embedding_health",
    "ElasticSearchRetriever",
    "SearchResult",
    "SearchParams",
    "get_retriever",
    "initialize_retriever",
    "search_documents",
    "get_retriever_health",
    "validate_retriever_index",
    "get_rag_agent",
    "initialize_rag_agent",
    "answer_query",
    "get_rag_health",
    "get_rag_info",
    "ProcessingMetrics"
] 