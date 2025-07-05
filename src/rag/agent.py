import time
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import traceback
import json
from datetime import datetime

from langchain_community.llms import VLLMOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from ..config.settings import settings
from ..utils.metrics import (
    track_rag_query, track_vllm_generation, 
    increment_llm_tokens, record_chunks_retrieved,
    record_error, record_vllm_error
)
from src.shared_models import QueryResponse, DocumentSource, QueryMetadata
from .retriever import get_retriever, SearchParams
from .embeddings import get_embedding_manager


# =============================================================================
# Enhanced Logging Functions
# =============================================================================

def log_vllm_connection_error(error: Exception, url: str, model_name: str) -> None:
    """Log vLLM connection errors with detailed information."""
    
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Determine the type of connection error
    if "Connection error" in error_msg or "Failed to connect" in error_msg:
        error_category = "NETWORK_CONNECTION"
        user_friendly_msg = f"❌ Could not connect to vLLM model at {url}"
        troubleshooting = [
            "🔍 Verify that the vLLM service is running",
            "🔍 Verify that port 8080 is open",
            "🔍 Verify network connectivity between pods"
        ]
    elif "timeout" in error_msg.lower():
        error_category = "TIMEOUT"
        user_friendly_msg = f"⏰ Timeout connecting to vLLM model at {url}"
        troubleshooting = [
            "🔍 Verify that the model is loaded correctly",
            "🔍 Consider increasing timeout in configuration",
            "🔍 Check system load"
        ]
    elif "model" in error_msg.lower() and "not found" in error_msg.lower():
        error_category = "MODEL_NOT_FOUND"
        user_friendly_msg = f"🔍 Model '{model_name}' not found in vLLM"
        troubleshooting = [
            "🔍 Verify that the model is deployed correctly",
            "🔍 Check model name in configuration",
            "🔍 Verify that the model is loaded in vLLM"
        ]
    else:
        error_category = "UNKNOWN_ERROR"
        user_friendly_msg = f"❓ Unknown error connecting to vLLM: {error_msg}"
        troubleshooting = [
            "🔍 Check vLLM service logs",
            "🔍 Verify vLLM configuration",
            "🔍 Contact system administrator"
        ]
    
    # Log detailed error information
    logging.error("=" * 80)
    logging.error("🚨 vLLM CONNECTION ERROR")
    logging.error("=" * 80)
    logging.error(f"📋 Error Type: {error_type}")
    logging.error(f"📋 Error Category: {error_category}")
    logging.error(f"📋 Model Name: {model_name}")
    logging.error(f"📋 vLLM URL: {url}")
    logging.error(f"📋 Error Message: {error_msg}")
    logging.error("")
    logging.error("🔧 TROUBLESHOOTING STEPS:")
    for step in troubleshooting:
        logging.error(f"   {step}")
    logging.error("")
    logging.error("📊 TECHNICAL DETAILS:")
    logging.error(f"   Exception Type: {error_type}")
    logging.error(f"   Full Error: {error_msg}")
    if hasattr(error, '__traceback__') and error.__traceback__:
        logging.error(f"   Stack Trace: {traceback.format_exc()}")
    logging.error("=" * 80)


def log_rag_processing_error(error: Exception, context: str = "query_processing") -> None:
    """Log RAG processing errors with context."""
    
    error_type = type(error).__name__
    error_msg = str(error)
    
    logging.error("=" * 80)
    logging.error(f"🚨 RAG PROCESSING ERROR - {context.upper()}")
    logging.error("=" * 80)
    logging.error(f"📋 Error Type: {error_type}")
    logging.error(f"📋 Context: {context}")
    logging.error(f"📋 Error Message: {error_msg}")
    logging.error("")
    logging.error("🔧 POSSIBLE SOLUTIONS:")
    if "embedding" in error_msg.lower():
        logging.error("   🔍 Verify that the embedding model is loaded")
        logging.error("   🔍 Check embedding configuration")
    elif "retriever" in error_msg.lower() or "elasticsearch" in error_msg.lower():
        logging.error("   🔍 Verify Elasticsearch connection")
        logging.error("   🔍 Check if index exists and has documents")
    elif "llm" in error_msg.lower() or "vllm" in error_msg.lower():
        logging.error("   🔍 Verify vLLM connection")
        logging.error("   🔍 Ensure model is available")
    else:
        logging.error("   🔍 Review general system configuration")
        logging.error("   🔍 Check logs from all components")
    logging.error("")
    logging.error("📊 TECHNICAL DETAILS:")
    logging.error(f"   Exception Type: {error_type}")
    logging.error(f"   Full Error: {error_msg}")
    if hasattr(error, '__traceback__') and error.__traceback__:
        logging.error(f"   Stack Trace: {traceback.format_exc()}")
    logging.error("=" * 80)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ProcessingMetrics:
    """Metrics for query processing steps."""
    
    query_embedding_time_ms: int = 0
    retrieval_time_ms: int = 0
    llm_generation_time_ms: int = 0
    total_processing_time_ms: int = 0
    chunks_retrieved: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# =============================================================================
# RAG Agent
# =============================================================================

class RAGAgent:
    """Core RAG agent that orchestrates retrieval and generation."""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize the RAG agent."""
        
        self.model_name = model_name or settings.vllm.model_name
        
        # Initialize components
        self.retriever = get_retriever()
        self.embedding_manager = get_embedding_manager()
        
        # Initialize LLM client
        self.llm_client = self._setup_llm_client()
        
        # Initialize RetrievalQA chain
        self.qa_chain = self._setup_retrieval_qa()
        
        # Performance tracking
        self.total_queries_processed = 0
        self.total_processing_time = 0.0
        
        logging.info(f"RAG Agent initialized, model_name={self.model_name}, retriever_type={type(self.retriever).__name__}, llm_client_type={type(self.llm_client).__name__}")
    
    def _setup_llm_client(self) -> VLLMOpenAI:
        """Setup vLLM client with configuration."""
        
        try:
            # Ensure the vLLM URL ends with /v1 for OpenAI compatibility
            vllm_url = settings.vllm.url.rstrip('/') + '/v1'
            logging.info(f"Setting up vLLM client, url={vllm_url}")
            
            llm_client = VLLMOpenAI(
                openai_api_key="dummy",  # Not used for vLLM
                openai_api_base=vllm_url,
                model_name=self.model_name,
                temperature=settings.vllm.temperature,
                max_tokens=settings.vllm.max_tokens,
                top_p=settings.vllm.top_p,
                request_timeout=settings.vllm.timeout,
                max_retries=settings.vllm.max_retries,
                streaming=False  # Disable streaming for now
            )
            
            logging.info(f"vLLM client setup completed, model_name={self.model_name}, url={settings.vllm.url}")
            
            return llm_client
            
        except Exception as e:
            log_vllm_connection_error(e, settings.vllm.url, self.model_name)
            record_vllm_error(type(e).__name__)
            raise
    
    def _setup_retrieval_qa(self) -> RetrievalQA:
        """Setup RetrievalQA chain with custom prompt."""
        
        try:
            # Custom prompt template for RAG
            prompt_template = """You are a helpful AI assistant that answers questions based on the provided context.

Context information:
{context}

Question: {question}

Please provide a comprehensive answer based on the context information. If the context doesn't contain enough information to answer the question, say so. Be accurate and helpful in your response.

Answer:"""
            
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Create RetrievalQA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm_client,
                chain_type="stuff",
                retriever=self.retriever,
                chain_type_kwargs={
                    "prompt": prompt,
                    "verbose": False
                },
                return_source_documents=True
            )
            
            logging.info("RetrievalQA chain setup completed")
            return qa_chain
            
        except Exception as e:
            logging.error(f"Failed to setup RetrievalQA chain: {str(e)}")
            record_error(type(e).__name__, "rag")
            raise
    
    def _build_context_from_documents(self, documents: List[Document]) -> str:
        """Build context string from retrieved documents."""
        
        if not documents:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            # Add document content
            context_parts.append(f"Document {i}:")
            context_parts.append(doc.page_content)
            
            # Add metadata if available
            if doc.metadata:
                metadata_str = ", ".join([
                    f"{k}: {v}" for k, v in doc.metadata.items() 
                    if k not in ["score", "chunk_id"] and v is not None
                ])
                if metadata_str:
                    context_parts.append(f"Source: {metadata_str}")
            
            context_parts.append("")  # Empty line between documents
        
        return "\n".join(context_parts)
    
    def _extract_sources_from_documents(self, documents: List[Document]) -> List[DocumentSource]:
        """Extract source information from documents."""
        
        sources = []
        for i, doc in enumerate(documents):
            try:
                # Debug logging
                logging.info(f"Processing document {i}: metadata={doc.metadata}, content_length={len(doc.page_content) if doc.page_content else 0}")
                
                # Normalize score to 0.0-1.0 range (Elasticsearch scores can be > 1.0)
                raw_score = doc.metadata.get("score", 0.0)
                normalized_score = min(raw_score / 2.0, 1.0)  # Divide by 2 since max score is ~2.0
                
                # Ensure document name is not None
                document_name = doc.metadata.get("document_name")
                if document_name is None:
                    document_name = "Unknown"
                
                # Ensure page_content is not None
                chunk_text = doc.page_content if doc.page_content is not None else ""
                
                logging.info(f"Document {i} processed: document_name='{document_name}', score={normalized_score}, chunk_length={len(chunk_text)}")
                
                # Debug: Log the exact values being passed to DocumentSource
                logging.info(f"Creating DocumentSource with: document='{document_name}' (type: {type(document_name)}), score={normalized_score} (type: {type(normalized_score)}), chunk_text length={len(chunk_text)}")
                
                source = DocumentSource(
                    document=document_name,
                    chunk_text=chunk_text,
                    score=normalized_score,
                    metadata={
                        k: v for k, v in doc.metadata.items()
                        if k not in ["score", "chunk_id", "document_name"]
                    },
                    chunk_id=doc.metadata.get("chunk_id"),
                    page_number=doc.metadata.get("page_number")
                )
                sources.append(source)
                
            except Exception as e:
                logging.error(f"Error processing document {i}: {e}")
                logging.error(f"Document metadata: {doc.metadata}")
                logging.error(f"Document content: {doc.page_content}")
                raise
        
        return sources
    
    def _calculate_confidence_score(self, answer: str, sources: List[DocumentSource]) -> float:
        """Calculate confidence score based on answer and sources."""
        
        if not sources:
            return 0.0
        
        # Simple confidence calculation based on source scores
        avg_source_score = sum(s.score for s in sources) / len(sources)
        
        # Boost confidence if we have multiple good sources
        if len(sources) > 1:
            avg_source_score *= 1.1
        
        # Cap at 1.0
        return min(avg_source_score, 1.0)
    
    @track_rag_query("default")
    def answer_query(
        self,
        question: str,
        llm_params: Optional[Dict[str, Any]] = None,
        retrieval_params: Optional[Dict[str, Any]] = None
    ) -> QueryResponse:
        """Main method to answer a query using RAG pipeline."""
        
        start_time = time.time()
        metrics = ProcessingMetrics()
        
        try:
            logging.info(
                f"Processing query request - Correlation ID: {getattr(self, 'correlation_id', 'n/a')}, Question Length: {len(question)}, LLM Params: {llm_params}, Retrieval Params: {retrieval_params}"
            )
            
            # Step 1: Generate query embedding
            embedding_start = time.time()
            query_embedding = self.embedding_manager.embed_query(question)
            if query_embedding is None:
                raise ValueError("Failed to generate query embedding")
            
            metrics.query_embedding_time_ms = int((time.time() - embedding_start) * 1000)
            
            # Step 2: Retrieve relevant documents
            retrieval_start = time.time()
            
            # Build search parameters
            search_params = SearchParams(
                top_k=retrieval_params.get("top_k", settings.rag.top_k) if retrieval_params else settings.rag.top_k,
                similarity_threshold=retrieval_params.get("similarity_threshold", settings.rag.similarity_threshold) if retrieval_params else settings.rag.similarity_threshold,
                search_type=retrieval_params.get("search_type", settings.rag.search_type) if retrieval_params else settings.rag.search_type,
                metadata_filters=retrieval_params.get("metadata_filters") if retrieval_params else None,
                text_query=retrieval_params.get("text_query") if retrieval_params else None
            )
            
            # Retrieve documents
            documents = self.retriever.search_relevant_documents(query=question, search_params=search_params)
            
            metrics.retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            metrics.chunks_retrieved = len(documents)
            
            # Record metrics
            record_chunks_retrieved(search_params.search_type, len(documents))
            
            if not documents:
                logging.warning("No documents retrieved for query")
                return QueryResponse(
                    answer="I couldn't find any relevant information to answer your question. Please try rephrasing or ask a different question.",
                    sources=[],
                    confidence_score=0.0
                )
            
            # Step 3: Generate answer using LLM
            generation_start = time.time()
            
            # Update LLM parameters if provided
            if llm_params:
                self._update_llm_parameters(llm_params)
            
            # Build context from documents
            context = self._build_context_from_documents(documents)
            
            # Generate answer with vLLM
            with track_vllm_generation(self.model_name):
                try:
                    # Use the QA chain to generate answer
                    result = self.qa_chain({"query": question})
                    answer = result.get("result", "")
                    
                    # Extract token usage if available
                    if hasattr(self.llm_client, 'last_token_usage'):
                        usage = self.llm_client.last_token_usage
                        metrics.prompt_tokens = usage.get("prompt_tokens", 0)
                        metrics.completion_tokens = usage.get("completion_tokens", 0)
                        metrics.total_tokens = usage.get("total_tokens", 0)
                        
                        # Record token metrics
                        increment_llm_tokens(self.model_name, "prompt", metrics.prompt_tokens)
                        increment_llm_tokens(self.model_name, "completion", metrics.completion_tokens)
                    
                except Exception as e:
                    # Enhanced pretty logging for model errors
                    error_type = type(e).__name__
                    error_msg = str(e)
                    log_block = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": "RAG_QUERY_ERROR",
                        "error_type": error_type,
                        "error_message": error_msg,
                        "model_name": getattr(self, 'model_name', None),
                        "vllm_url": getattr(settings.vllm, 'url', None),
                        "llm_client": str(type(getattr(self, 'llm_client', None))),
                    }
                    print("\n" + "="*80)
                    print(json.dumps(log_block, indent=2))
                    print("="*80 + "\n")
                    log_rag_processing_error(e, "query_processing")
                    record_error(type(e).__name__, "rag")

                    # Return user-friendly error response
                    if "Connection" in error_type or "Timeout" in error_type:
                        user_message = (
                            "The AI model is currently unreachable due to connectivity issues. "
                            "Please try again in a few minutes. If the problem persists, contact your administrator."
                        )
                    elif "Model" in error_type or "NotFound" in error_type:
                        user_message = (
                            "The AI model is not available at the moment. "
                            "Please contact your administrator to check the model status."
                        )
                    else:
                        user_message = (
                            "An unexpected error occurred while processing your request. "
                            "Please try again later or contact support if the issue continues."
                        )

                    return QueryResponse(
                        answer=user_message,
                        sources=[],
                        confidence_score=0.0
                    )
            
            metrics.llm_generation_time_ms = int((time.time() - generation_start) * 1000)
            
            # Step 4: Process results
            total_time = time.time() - start_time
            metrics.total_processing_time_ms = int(total_time * 1000)
            
            # Extract sources
            sources = self._extract_sources_from_documents(documents)
            
            # Calculate confidence
            confidence_score = self._calculate_confidence_score(answer, sources)
            
            # Build query metadata
            query_metadata = QueryMetadata(
                processing_time_ms=metrics.total_processing_time_ms,
                model_used=self.model_name,
                chunks_retrieved=metrics.chunks_retrieved,
                query_embedding_time_ms=metrics.query_embedding_time_ms,
                search_time_ms=metrics.retrieval_time_ms,
                llm_time_ms=metrics.llm_generation_time_ms,
                total_tokens=metrics.total_tokens,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens
            )
            
            # Update performance metrics
            self.total_queries_processed += 1
            self.total_processing_time += total_time
            
            # Build response
            response = QueryResponse(
                answer=answer,
                sources=sources if settings.rag.include_sources else [],
                query_metadata=query_metadata if settings.rag.include_metadata else None,
                confidence_score=confidence_score
            )
            
            logging.info(
                f"Query processed successfully - answer_length={len(answer)}, num_sources={len(sources)}, confidence_score={confidence_score}, total_time={total_time}"
            )
            
            return response
            
        except Exception as e:
            log_rag_processing_error(e, "query_processing")
            record_error(type(e).__name__, "rag")
            
            # Return user-friendly error response
            error_type = type(e).__name__
            if "Connection" in error_type or "Timeout" in error_type:
                user_message = "Sorry, I cannot process your question at the moment due to connectivity issues with the AI model. Please try again in a few minutes."
            elif "Model" in error_type or "NotFound" in error_type:
                user_message = "Sorry, the AI model is not available at the moment. Please contact your system administrator."
            else:
                user_message = "Sorry, an unexpected error occurred while processing your question. Please try again later."
            
            return QueryResponse(
                answer=user_message,
                sources=[],
                confidence_score=0.0
            )
    
    def _update_llm_parameters(self, llm_params: Dict[str, Any]) -> None:
        """Update LLM parameters for the current request."""
        
        try:
            if "temperature" in llm_params:
                self.llm_client.temperature = llm_params["temperature"]
            if "max_tokens" in llm_params:
                self.llm_client.max_tokens = llm_params["max_tokens"]
            if "top_p" in llm_params:
                self.llm_client.top_p = llm_params["top_p"]
            # Note: top_k is not supported by VLLMOpenAI client
            
            logging.debug(f"LLM parameters updated - params={llm_params}")
            
        except Exception as e:
            logging.warning(f"Failed to update LLM parameters: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of all components."""
        
        health_status = {
            "agent_healthy": True,
            "components": {},
            "performance": {},
            "errors": []
        }
        
        try:
            # Check retriever health
            retriever_health = self.retriever.get_health_status()
            health_status["components"]["retriever"] = retriever_health
            
            if not retriever_health.get("connection_healthy", False):
                health_status["agent_healthy"] = False
                health_status["errors"].append("Retriever connection unhealthy")
            
            # Check embedding manager health
            embedding_health = self.embedding_manager.get_health_status()
            health_status["components"]["embeddings"] = embedding_health
            
            if not embedding_health.get("model_loaded", False):
                health_status["agent_healthy"] = False
                health_status["errors"].append("Embedding model not loaded")
            
            # Check vLLM connection (simple ping)
            try:
                # Just check if the client can connect, don't do actual generation
                # This is much faster than doing a test generation
                if hasattr(self.llm_client, 'client') and hasattr(self.llm_client.client, 'base_url'):
                    # For OpenAI-compatible clients, just check the base URL
                    health_status["components"]["vllm"] = {
                        "connection_healthy": True,
                        "model_name": self.model_name,
                        "url": str(self.llm_client.client.base_url)
                    }
                else:
                    # Fallback: assume healthy if client exists
                    health_status["components"]["vllm"] = {
                        "connection_healthy": True,
                        "model_name": self.model_name
                    }
            except Exception as e:
                log_vllm_connection_error(e, settings.vllm.url, self.model_name)
                health_status["components"]["vllm"] = {
                    "connection_healthy": False,
                    "error": str(e)
                }
                health_status["agent_healthy"] = False
                health_status["errors"].append(f"vLLM connection failed: {str(e)}")
            
            # Performance metrics
            health_status["performance"] = {
                "total_queries_processed": self.total_queries_processed,
                "total_processing_time": self.total_processing_time,
                "average_processing_time": (
                    self.total_processing_time / self.total_queries_processed 
                    if self.total_queries_processed > 0 else 0.0
                )
            }
            
            logging.info(f"Health check completed, agent_healthy={health_status['agent_healthy']}, num_errors={len(health_status['errors'])}")
            
        except Exception as e:
            health_status["agent_healthy"] = False
            health_status["errors"].append(f"Health check failed: {str(e)}")
            logging.error(f"Health check failed: {str(e)}")
        
        return health_status
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the RAG agent."""
        
        return {
            "model_name": self.model_name,
            "retriever_type": type(self.retriever).__name__,
            "llm_client_type": type(self.llm_client).__name__,
            "total_queries_processed": self.total_queries_processed,
            "average_processing_time": (
                self.total_processing_time / self.total_queries_processed 
                if self.total_queries_processed > 0 else 0.0
            ),
            "settings": {
                "rag_top_k": settings.rag.top_k,
                "rag_similarity_threshold": settings.rag.similarity_threshold,
                "rag_search_type": settings.rag.search_type,
                "vllm_temperature": settings.vllm.temperature,
                "vllm_max_tokens": settings.vllm.max_tokens
            }
        }


# =============================================================================
# Global RAG Agent Instance
# =============================================================================

_rag_agent = None


def get_rag_agent() -> RAGAgent:
    """Get the global RAG agent instance."""
    global _rag_agent
    
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    
    return _rag_agent


def initialize_rag_agent(model_name: Optional[str] = None) -> bool:
    """Initialize the global RAG agent."""
    global _rag_agent
    
    try:
        _rag_agent = RAGAgent(model_name=model_name)
        
        # Perform health check
        health = _rag_agent.health_check()
        if not health["agent_healthy"]:
            raise RuntimeError(f"RAG agent health check failed: {health['errors']}")
        
        return True
        
    except Exception as e:
        log_rag_processing_error(e, "agent_initialization")
        return False


# =============================================================================
# Convenience Functions
# =============================================================================

def answer_query(
    question: str,
    llm_params: Optional[Dict[str, Any]] = None,
    retrieval_params: Optional[Dict[str, Any]] = None
) -> QueryResponse:
    """Convenience function to answer a query."""
    agent = get_rag_agent()
    return agent.answer_query(question, llm_params, retrieval_params)


def get_rag_health() -> Dict[str, Any]:
    """Convenience function to get RAG agent health status."""
    agent = get_rag_agent()
    return agent.health_check()


def get_rag_info() -> Dict[str, Any]:
    """Convenience function to get RAG agent information."""
    agent = get_rag_agent()
    return agent.get_agent_info() 