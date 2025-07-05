from typing import Optional, List, Dict, Any
from datetime import datetime
from src.shared_models import DocumentSource, QueryMetadata, QueryResponse
from pydantic import BaseModel, Field, validator


# =============================================================================
# Request Models
# =============================================================================

class LLMParams(BaseModel):
    """LLM generation parameters for customizing responses."""
    
    model: Optional[str] = Field(
        default=None, 
        description="LLM model to use for generation"
    )
    temperature: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=2.0, 
        description="Sampling temperature (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=4096, 
        description="Maximum tokens to generate (1-4096)"
    )
    top_p: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Top-p sampling parameter (0.0-1.0)"
    )
    top_k: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=100, 
        description="Top-k sampling parameter (1-100)"
    )


class RetrievalParams(BaseModel):
    """Retrieval parameters for customizing document search."""
    
    top_k: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=20, 
        description="Number of documents to retrieve (1-20)"
    )
    similarity_threshold: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Minimum similarity score (0.0-1.0)"
    )
    search_type: Optional[str] = Field(
        default=None, 
        description="Search type: vector, hybrid, or keyword"
    )
    
    @validator('search_type')
    def validate_search_type(cls, v):
        if v is not None and v not in ['vector', 'hybrid', 'keyword']:
            raise ValueError('Search type must be vector, hybrid, or keyword')
        return v


class QueryRequest(BaseModel):
    """Main query request model for RAG API."""
    
    question: str = Field(
        ..., 
        min_length=1, 
        max_length=2000, 
        description="User question to process"
    )
    llm_params: Optional[LLMParams] = Field(
        default=None, 
        description="Custom LLM parameters"
    )
    retrieval_params: Optional[RetrievalParams] = Field(
        default=None, 
        description="Custom retrieval parameters"
    )
    include_sources: Optional[bool] = Field(
        default=True, 
        description="Include source documents in response"
    )
    include_metadata: Optional[bool] = Field(
        default=True, 
        description="Include processing metadata in response"
    )


# =============================================================================
# Health & Status Models
# =============================================================================

class ComponentStatus(BaseModel):
    """Status of individual components."""
    
    status: str = Field(description="Component status: healthy, unhealthy, or degraded")
    response_time_ms: Optional[int] = Field(
        default=None, 
        description="Response time in milliseconds"
    )
    error_message: Optional[str] = Field(
        default=None, 
        description="Error message if component is unhealthy"
    )
    last_check: datetime = Field(description="Timestamp of last health check")


class HealthResponse(BaseModel):
    """Health check response for monitoring."""
    
    status: str = Field(description="Overall status: healthy, unhealthy, or degraded")
    components: Dict[str, ComponentStatus] = Field(
        description="Status of individual components"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Health check timestamp"
    )
    version: str = Field(description="API version")
    uptime_seconds: Optional[int] = Field(
        default=None, 
        description="Application uptime in seconds"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(description="Error type/code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Error timestamp"
    )
    request_id: Optional[str] = Field(
        default=None, 
        description="Request ID for tracking"
    )


# =============================================================================
# Streamlit-specific Models
# =============================================================================

class StreamlitQueryRequest(BaseModel):
    """Simplified request model optimized for Streamlit."""
    
    question: str = Field(
        ..., 
        min_length=1, 
        max_length=2000, 
        description="User question"
    )
    temperature: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=2.0, 
        description="Response creativity (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=4096, 
        description="Maximum response length"
    )
    top_k: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=20, 
        description="Number of sources to use"
    )


class StreamlitQueryResponse(BaseModel):
    """Simplified response model optimized for Streamlit."""
    
    answer: str = Field(description="Generated answer")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Simplified source information"
    )
    processing_time: float = Field(description="Processing time in seconds")
    model_used: str = Field(description="Model used for generation")
    confidence: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Answer confidence score"
    )


# =============================================================================
# API Routes Models
# =============================================================================

class SimpleHealthResponse(BaseModel):
    """Simple health check response for API routes."""
    
    status: str = Field(description="Health status: healthy, ready, or unhealthy")
    timestamp: float = Field(description="Unix timestamp")
    version: str = Field(description="API version")
    service: str = Field(description="Service name")
    components: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Component health details"
    )
    performance: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Performance metrics"
    )


class InfoResponse(BaseModel):
    """API information response."""
    
    name: str = Field(description="API name")
    version: str = Field(description="API version")
    description: str = Field(description="API description")
    build_date: Optional[str] = Field(
        default=None, 
        description="Build date"
    )
    git_commit: Optional[str] = Field(
        default=None, 
        description="Git commit hash"
    )
    environment: str = Field(description="Environment name")
    rag_agent: Dict[str, Any] = Field(description="RAG agent information")
    settings: Dict[str, Any] = Field(description="Configuration settings")


class ModelInfo(BaseModel):
    """Model information for API routes."""
    
    name: str = Field(description="Model name")
    type: str = Field(description="Model type: llm or embedding")
    provider: str = Field(description="Model provider")
    url: str = Field(description="Model URL or location")
    parameters: Dict[str, Any] = Field(description="Model parameters") 