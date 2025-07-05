from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DocumentSource(BaseModel):
    """Represents a source document used in the response."""
    document: str = Field(description="Source document name/path")
    chunk_text: str = Field(description="Relevant text chunk from document")
    score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Relevance score (0.0-1.0)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional document metadata"
    )
    chunk_id: Optional[str] = Field(
        default=None, 
        description="Unique identifier for the chunk"
    )
    page_number: Optional[int] = Field(
        default=None, 
        description="Page number if applicable"
    )

class QueryMetadata(BaseModel):
    """Processing metadata and performance metrics."""
    processing_time_ms: int = Field(
        ge=0, 
        description="Total processing time in milliseconds"
    )
    model_used: str = Field(description="LLM model used for generation")
    chunks_retrieved: int = Field(
        ge=0, 
        description="Number of document chunks retrieved"
    )
    query_embedding_time_ms: int = Field(
        ge=0, 
        description="Time spent on query embedding"
    )
    search_time_ms: int = Field(
        ge=0, 
        description="Time spent on vector search"
    )
    llm_time_ms: int = Field(
        ge=0, 
        description="Time spent on LLM generation"
    )
    total_tokens: Optional[int] = Field(
        default=None, 
        description="Total tokens used in generation"
    )
    prompt_tokens: Optional[int] = Field(
        default=None, 
        description="Tokens in the prompt"
    )
    completion_tokens: Optional[int] = Field(
        default=None, 
        description="Tokens in the completion"
    )

class QueryResponse(BaseModel):
    """Main response model for RAG queries."""
    answer: str = Field(description="Generated answer from the LLM")
    sources: List[DocumentSource] = Field(
        default_factory=list, 
        description="Source documents used for generation"
    )
    query_metadata: Optional[QueryMetadata] = Field(
        default=None, 
        description="Processing metadata and metrics"
    )
    confidence_score: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the answer"
    ) 