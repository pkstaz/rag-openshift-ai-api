import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from langchain.llms import VLLMOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from ..config.settings import settings
from ..utils.logging import get_logger, log_performance
from ..utils.metrics import (
    track_rag_query, track_vllm_generation, 
    increment_llm_tokens, record_chunks_retrieved,
    record_error, record_vllm_error
)
from ..api.models import QueryResponse, DocumentSource, QueryMetadata
from .retriever import get_retriever, SearchParams
from .embeddings import get_embedding_manager


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
        
        self.logger = get_logger("rag.agent")
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
        
        self.logger.info(
            "RAG Agent initialized",
            model_name=self.model_name,
            retriever_type=type(self.retriever).__name__,
            llm_client_type=type(self.llm_client).__name__
        )
    
    def _setup_llm_client(self) -> VLLMOpenAI:
        """Setup vLLM client with configuration."""
        
        try:
            self.logger.info("Setting up vLLM client", url=settings.vllm.url)
            
            llm_client = VLLMOpenAI(
                openai_api_key="dummy",  # Not used for vLLM
                openai_api_base=settings.vllm.url,
                model_name=self.model_name,
                temperature=settings.vllm.temperature,
                max_tokens=settings.vllm.max_tokens,
                top_p=settings.vllm.top_p,
                top_k=settings.vllm.top_k,
                request_timeout=settings.vllm.timeout,
                max_retries=settings.vllm.max_retries,
                streaming=False  # Disable streaming for now
            )
            
            self.logger.info(
                "vLLM client setup completed",
                model_name=self.model_name,
                url=settings.vllm.url
            )
            
            return llm_client
            
        except Exception as e:
            self.logger.error(
                "Failed to setup vLLM client",
                error=str(e),
                error_type=type(e).__name__
            )
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
            
            self.logger.info("RetrievalQA chain setup completed")
            return qa_chain
            
        except Exception as e:
            self.logger.error(
                "Failed to setup RetrievalQA chain",
                error=str(e),
                error_type=type(e).__name__
            )
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
        for doc in documents:
            source = DocumentSource(
                document=doc.metadata.get("document_name", "Unknown"),
                chunk_text=doc.page_content,
                score=doc.metadata.get("score", 0.0),
                metadata={
                    k: v for k, v in doc.metadata.items()
                    if k not in ["score", "chunk_id", "document_name"]
                },
                chunk_id=doc.metadata.get("chunk_id"),
                page_number=doc.metadata.get("page_number")
            )
            sources.append(source)
        
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
            self.logger.info(
                "Processing query",
                question_length=len(question),
                llm_params=llm_params,
                retrieval_params=retrieval_params
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
            documents = self.retriever._get_relevant_documents(question, search_params)
            
            metrics.retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            metrics.chunks_retrieved = len(documents)
            
            # Record metrics
            record_chunks_retrieved(search_params.search_type, len(documents))
            
            if not documents:
                self.logger.warning("No documents retrieved for query")
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
                    self.logger.error(
                        "LLM generation failed",
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    record_vllm_error(type(e).__name__)
                    raise
            
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
            
            self.logger.info(
                "Query processed successfully",
                answer_length=len(answer),
                num_sources=len(sources),
                confidence_score=confidence_score,
                total_time=total_time
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Error processing query",
                question=question,
                error=str(e),
                error_type=type(e).__name__
            )
            record_error(type(e).__name__, "rag")
            
            # Return error response
            return QueryResponse(
                answer=f"I encountered an error while processing your question: {str(e)}. Please try again later.",
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
            if "top_k" in llm_params:
                self.llm_client.top_k = llm_params["top_k"]
            
            self.logger.debug("LLM parameters updated", params=llm_params)
            
        except Exception as e:
            self.logger.warning(
                "Failed to update LLM parameters",
                error=str(e),
                error_type=type(e).__name__
            )
    
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
                # Try a simple generation to test connection
                test_result = self.llm_client.generate(["test"])
                health_status["components"]["vllm"] = {
                    "connection_healthy": True,
                    "model_name": self.model_name
                }
            except Exception as e:
                health_status["components"]["vllm"] = {
                    "connection_healthy": False,
                    "error": str(e),
                    "error_type": type(e).__name__
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
            
            self.logger.info(
                "Health check completed",
                agent_healthy=health_status["agent_healthy"],
                num_errors=len(health_status["errors"])
            )
            
        except Exception as e:
            health_status["agent_healthy"] = False
            health_status["errors"].append(f"Health check failed: {str(e)}")
            self.logger.error(
                "Health check failed",
                error=str(e),
                error_type=type(e).__name__
            )
        
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

_rag_agent: Optional[RAGAgent] = None


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
        logger = get_logger("rag.agent")
        logger.error(
            "Failed to initialize RAG agent",
            error=str(e),
            error_type=type(e).__name__
        )
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