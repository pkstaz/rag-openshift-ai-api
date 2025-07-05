from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class APISettings(BaseSettings):
    """API configuration settings."""
    
    title: str = Field(default="RAG OpenShift AI API", description="API title")
    version: str = Field(default="0.1.0", description="API version")
    description: str = Field(default="RAG agent for OpenShift AI", description="API description")
    
    host: str = Field(default="0.0.0.0", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")
    
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")
    
    cors_origins: List[str] = Field(
        default=["*"], 
        description="CORS allowed origins"
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], 
        description="CORS allowed methods"
    )
    
    docs_enabled: bool = Field(default=True, description="Enable OpenAPI docs (Swagger/Redoc)")
    cors_enabled: bool = Field(default=True, description="Enable CORS middleware")
    
    class Config:
        env_prefix = "API_"
        env_file = ".env"
        model_config = {
            "protected_namespaces": ()
        }


class ElasticsearchSettings(BaseSettings):
    """Elasticsearch configuration settings."""
    
    url: str = Field(default="https://localhost:9200", description="Elasticsearch URL")
    index_name: str = Field(default="rag_documents", description="Index name for documents")
    
    username: Optional[str] = Field(default=None, description="Elasticsearch username")
    password: Optional[str] = Field(default=None, description="Elasticsearch password")
    
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    vector_dimension: int = Field(default=384, description="Vector dimension for embeddings")
    
    class Config:
        env_prefix = "ES_"
        env_file = ".env"
        model_config = {
            "protected_namespaces": ()
        }


class VLLMSettings(BaseSettings):
    """vLLM configuration settings."""
    
    url: str = Field(default="http://localhost:8080", description="vLLM server URL")
    model_name: str = Field(default="granite-3-1-8b-instruct", description="Default model name")
    
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # Generation parameters
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=512, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, description="Top-p sampling parameter")
    top_k: int = Field(default=50, description="Top-k sampling parameter")
    
    class Config:
        env_prefix = "VLLM_"
        env_file = ".env"
        model_config = {
            "protected_namespaces": ()
        }


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration settings."""
    
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        description="Embedding model name"
    )
    device: str = Field(default="cpu", description="Device for model inference")
    batch_size: int = Field(default=32, description="Batch size for processing")
    
    normalize_embeddings: bool = Field(
        default=True, 
        description="Normalize embeddings for cosine similarity"
    )
    
    @validator('device')
    def validate_device(cls, v):
        if v not in ['cpu', 'cuda', 'mps']:
            raise ValueError('Device must be cpu, cuda, or mps')
        return v
    
    class Config:
        env_prefix = "EMBEDDING_"
        env_file = ".env"
        model_config = {
            "protected_namespaces": ()
        }


class RAGSettings(BaseSettings):
    """RAG pipeline configuration settings."""
    
    top_k: int = Field(default=5, description="Number of documents to retrieve")
    similarity_threshold: float = Field(
        default=0.7, 
        description="Minimum similarity score for retrieval"
    )
    
    search_type: str = Field(
        default="vector", 
        description="Search type: vector, hybrid, or keyword"
    )
    
    # Response formatting
    include_metadata: bool = Field(
        default=True, 
        description="Include document metadata in response"
    )
    include_sources: bool = Field(
        default=True, 
        description="Include source documents in response"
    )
    
    # Chunking settings
    chunk_size: int = Field(default=1000, description="Document chunk size")
    chunk_overlap: int = Field(default=200, description="Chunk overlap size")
    
    class Config:
        env_prefix = "RAG_"
        env_file = ".env"
        model_config = {
            "protected_namespaces": ()
        }


class EnvironmentConfig(BaseSettings):
    """Environment configuration."""
    secret_key: str = Field(
        default="your-secret-key-change-this-in-deployment",
        description="Secret key for application"
    )
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")


class LoggingSettings(BaseSettings):
    level: str = Field(default="INFO", description="Logging level")

    class Config:
        env_prefix = "LOGGING_"
        env_file = ".env"


class MetricsSettings(BaseSettings):
    enabled: bool = Field(default=True, description="Enable metrics collection")
    host: str = Field(default="0.0.0.0", description="Metrics server host")
    port: int = Field(default=9000, description="Metrics server port")

    class Config:
        env_prefix = "METRICS_"
        env_file = ".env"


class Settings(BaseSettings):
    """Main application settings combining all configuration sections."""
    
    api: APISettings = Field(default_factory=APISettings)
    elasticsearch: ElasticsearchSettings = Field(default_factory=ElasticsearchSettings)
    vllm: VLLMSettings = Field(default_factory=VLLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # For OpenShift: variables will be injected via ConfigMap/Secret
        # No need to read from .env file in production
        model_config = {
            "protected_namespaces": ("settings_",)
        }


# Global settings instance
settings = Settings() 