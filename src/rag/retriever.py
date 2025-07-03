import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import numpy as np

from elasticsearch import Elasticsearch, ConnectionTimeout, NotFoundError
from elasticsearch.exceptions import ElasticsearchException
from langchain.schema import BaseRetriever, Document
from langchain.callbacks.manager import CallbackManagerForRetrieverRun

from ..config.settings import settings
from ..utils.logging import get_logger, log_performance
from ..utils.metrics import track_elasticsearch_search, record_elasticsearch_error
from .embeddings import get_embedding_manager


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SearchResult:
    """Represents a search result from Elasticsearch."""
    
    text: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: Optional[str] = None
    document_name: Optional[str] = None


@dataclass
class SearchParams:
    """Parameters for search operations."""
    
    top_k: int = 5
    similarity_threshold: float = 0.7
    search_type: str = "vector"  # vector, hybrid, keyword
    metadata_filters: Optional[Dict[str, Any]] = None
    text_query: Optional[str] = None


# =============================================================================
# ElasticSearch Retriever
# =============================================================================

class ElasticSearchRetriever(BaseRetriever):
    """Custom ElasticSearch retriever for RAG applications."""
    
    def __init__(
        self,
        index_name: Optional[str] = None,
        embedding_field: str = "embedding",
        text_field: str = "text",
        metadata_fields: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize the ElasticSearch retriever."""
        
        super().__init__(**kwargs)
        
        self.logger = get_logger("rag.retriever")
        self.index_name = index_name or settings.elasticsearch.index_name
        self.embedding_field = embedding_field
        self.text_field = text_field
        self.metadata_fields = metadata_fields or [
            "filename", "chunk_id", "page_number", "document_type"
        ]
        
        # Initialize ElasticSearch client
        self.es_client = self._initialize_es_client()
        
        # Initialize embedding manager
        self.embedding_manager = get_embedding_manager()
        
        # Performance tracking
        self.total_searches = 0
        self.total_results = 0
        self.total_search_time = 0.0
        
        self.logger.info(
            "ElasticSearch retriever initialized",
            index_name=self.index_name,
            embedding_field=self.embedding_field,
            text_field=self.text_field
        )
    
    def _initialize_es_client(self) -> Elasticsearch:
        """Initialize ElasticSearch client with configuration."""
        
        try:
            # Build connection parameters
            es_config = {
                "hosts": [settings.elasticsearch.url],
                "timeout": settings.elasticsearch.timeout,
                "retry_on_timeout": settings.elasticsearch.retry_on_timeout,
                "max_retries": settings.elasticsearch.max_retries,
            }
            
            # Add authentication if provided
            if settings.elasticsearch.username and settings.elasticsearch.password:
                es_config["basic_auth"] = (
                    settings.elasticsearch.username,
                    settings.elasticsearch.password
                )
            
            # Create client
            client = Elasticsearch(**es_config)
            
            # Test connection
            if not client.ping():
                raise ConnectionError("Failed to connect to Elasticsearch")
            
            self.logger.info(
                "ElasticSearch client initialized successfully",
                url=settings.elasticsearch.url,
                index_name=self.index_name
            )
            
            return client
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize ElasticSearch client",
                error=str(e),
                error_type=type(e).__name__
            )
            record_elasticsearch_error(type(e).__name__)
            raise
    
    def _build_vector_query(
        self, 
        query_embedding: np.ndarray, 
        search_params: SearchParams
    ) -> Dict[str, Any]:
        """Build ElasticSearch query for vector similarity search."""
        
        query = {
            "size": search_params.top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {
                            "query_vector": query_embedding.tolist()
                        }
                    }
                }
            },
            "_source": {
                "includes": [self.text_field] + self.metadata_fields
            }
        }
        
        # Add metadata filters if provided
        if search_params.metadata_filters:
            filter_conditions = []
            for field, value in search_params.metadata_filters.items():
                if isinstance(value, list):
                    filter_conditions.append({"terms": {field: value}})
                else:
                    filter_conditions.append({"term": {field: value}})
            
            if filter_conditions:
                query["query"]["script_score"]["query"] = {
                    "bool": {"filter": filter_conditions}
                }
        
        return query
    
    def _build_hybrid_query(
        self, 
        query_embedding: np.ndarray, 
        text_query: str,
        search_params: SearchParams
    ) -> Dict[str, Any]:
        """Build ElasticSearch query for hybrid search (vector + text)."""
        
        query = {
            "size": search_params.top_k,
            "query": {
                "script_score": {
                    "query": {
                        "multi_match": {
                            "query": text_query,
                            "fields": [self.text_field, "title^2"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {
                            "query_vector": query_embedding.tolist()
                        }
                    }
                }
            },
            "_source": {
                "includes": [self.text_field] + self.metadata_fields
            }
        }
        
        # Add metadata filters if provided
        if search_params.metadata_filters:
            filter_conditions = []
            for field, value in search_params.metadata_filters.items():
                if isinstance(value, list):
                    filter_conditions.append({"terms": {field: value}})
                else:
                    filter_conditions.append({"term": {field: value}})
            
            if filter_conditions:
                query["query"]["script_score"]["query"] = {
                    "bool": {
                        "must": query["query"]["script_score"]["query"],
                        "filter": filter_conditions
                    }
                }
        
        return query
    
    def _build_keyword_query(
        self, 
        text_query: str,
        search_params: SearchParams
    ) -> Dict[str, Any]:
        """Build ElasticSearch query for keyword search only."""
        
        query = {
            "size": search_params.top_k,
            "query": {
                "multi_match": {
                    "query": text_query,
                    "fields": [self.text_field, "title^2"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "_source": {
                "includes": [self.text_field] + self.metadata_fields
            }
        }
        
        # Add metadata filters if provided
        if search_params.metadata_filters:
            filter_conditions = []
            for field, value in search_params.metadata_filters.items():
                if isinstance(value, list):
                    filter_conditions.append({"terms": {field: value}})
                else:
                    filter_conditions.append({"term": {field: value}})
            
            if filter_conditions:
                query["query"] = {
                    "bool": {
                        "must": query["query"],
                        "filter": filter_conditions
                    }
                }
        
        return query
    
    def _execute_search(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search query against Elasticsearch."""
        
        try:
            with track_elasticsearch_search("vector"):
                start_time = time.time()
                
                response = self.es_client.search(
                    index=self.index_name,
                    body=query,
                    timeout=f"{settings.elasticsearch.timeout}s"
                )
                
                search_time = time.time() - start_time
                
                # Update performance metrics
                self.total_searches += 1
                self.total_search_time += search_time
                
                self.logger.debug(
                    "Search executed successfully",
                    search_time=search_time,
                    total_hits=response["hits"]["total"]["value"]
                )
                
                return response
                
        except ConnectionTimeout:
            self.logger.error("ElasticSearch search timeout")
            record_elasticsearch_error("ConnectionTimeout")
            raise
        except NotFoundError:
            self.logger.error(f"Index {self.index_name} not found")
            record_elasticsearch_error("NotFoundError")
            raise
        except ElasticsearchException as e:
            self.logger.error(
                "ElasticSearch search error",
                error=str(e),
                error_type=type(e).__name__
            )
            record_elasticsearch_error(type(e).__name__)
            raise
    
    def _process_results(
        self, 
        response: Dict[str, Any], 
        search_params: SearchParams
    ) -> List[SearchResult]:
        """Process ElasticSearch response into SearchResult objects."""
        
        results = []
        
        try:
            hits = response["hits"]["hits"]
            
            for hit in hits:
                score = hit["_score"]
                
                # Apply similarity threshold
                if score < search_params.similarity_threshold:
                    continue
                
                source = hit["_source"]
                text = source.get(self.text_field, "")
                
                # Extract metadata
                metadata = {}
                for field in self.metadata_fields:
                    if field in source:
                        metadata[field] = source[field]
                
                # Create search result
                result = SearchResult(
                    text=text,
                    metadata=metadata,
                    score=score,
                    chunk_id=metadata.get("chunk_id"),
                    document_name=metadata.get("filename")
                )
                
                results.append(result)
            
            # Sort by score (descending)
            results.sort(key=lambda x: x.score, reverse=True)
            
            # Limit to top_k
            results = results[:search_params.top_k]
            
            self.total_results += len(results)
            
            self.logger.debug(
                "Results processed",
                total_hits=len(hits),
                filtered_results=len(results),
                top_score=results[0].score if results else 0.0
            )
            
        except Exception as e:
            self.logger.error(
                "Error processing search results",
                error=str(e),
                error_type=type(e).__name__
            )
            record_elasticsearch_error("ResultProcessingError")
        
        return results
    
    def _get_relevant_documents(
        self, 
        query: str,
        search_params: Optional[SearchParams] = None
    ) -> List[Document]:
        """Get relevant documents for the query (LangChain interface)."""
        
        if search_params is None:
            search_params = SearchParams()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_manager.embed_query(query)
            if query_embedding is None:
                self.logger.error("Failed to generate query embedding")
                return []
            
            # Build query based on search type
            if search_params.search_type == "vector":
                es_query = self._build_vector_query(query_embedding, search_params)
            elif search_params.search_type == "hybrid" and search_params.text_query:
                es_query = self._build_hybrid_query(
                    query_embedding, 
                    search_params.text_query, 
                    search_params
                )
            elif search_params.search_type == "keyword" and search_params.text_query:
                es_query = self._build_keyword_query(search_params.text_query, search_params)
            else:
                # Fallback to vector search
                es_query = self._build_vector_query(query_embedding, search_params)
            
            # Execute search
            response = self._execute_search(es_query)
            
            # Process results
            search_results = self._process_results(response, search_params)
            
            # Convert to LangChain Documents
            documents = []
            for result in search_results:
                doc = Document(
                    page_content=result.text,
                    metadata={
                        "score": result.score,
                        "chunk_id": result.chunk_id,
                        "document_name": result.document_name,
                        **result.metadata
                    }
                )
                documents.append(doc)
            
            self.logger.info(
                "Retrieved documents",
                query_length=len(query),
                search_type=search_params.search_type,
                num_documents=len(documents),
                top_score=documents[0].metadata["score"] if documents else 0.0
            )
            
            return documents
            
        except Exception as e:
            self.logger.error(
                "Error retrieving documents",
                query=query,
                error=str(e),
                error_type=type(e).__name__
            )
            record_elasticsearch_error("RetrievalError")
            return []
    
    async def _aget_relevant_documents(
        self, 
        query: str,
        search_params: Optional[SearchParams] = None,
        *, 
        run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Async version of _get_relevant_documents."""
        
        # For now, use synchronous version
        # In the future, this could be made truly async
        return self._get_relevant_documents(query, search_params)
    
    def search(
        self, 
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        search_type: str = "vector",
        metadata_filters: Optional[Dict[str, Any]] = None,
        text_query: Optional[str] = None
    ) -> List[SearchResult]:
        """Search for documents with custom parameters."""
        
        search_params = SearchParams(
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            search_type=search_type,
            metadata_filters=metadata_filters,
            text_query=text_query
        )
        
        documents = self._get_relevant_documents(query, search_params)
        
        # Convert back to SearchResult objects
        results = []
        for doc in documents:
            result = SearchResult(
                text=doc.page_content,
                metadata=doc.metadata,
                score=doc.metadata.get("score", 0.0),
                chunk_id=doc.metadata.get("chunk_id"),
                document_name=doc.metadata.get("document_name")
            )
            results.append(result)
        
        return results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the ElasticSearch retriever."""
        
        try:
            # Test connection
            cluster_info = self.es_client.info()
            index_stats = self.es_client.indices.stats(index=self.index_name)
            
            return {
                "connection_healthy": True,
                "cluster_name": cluster_info.get("cluster_name"),
                "elasticsearch_version": cluster_info.get("version", {}).get("number"),
                "index_name": self.index_name,
                "index_document_count": index_stats["indices"][self.index_name]["total"]["docs"]["count"],
                "index_size_bytes": index_stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "total_searches": self.total_searches,
                "total_results": self.total_results,
                "average_search_time": (
                    self.total_search_time / self.total_searches 
                    if self.total_searches > 0 else 0.0
                )
            }
            
        except Exception as e:
            self.logger.error(
                "Health check failed",
                error=str(e),
                error_type=type(e).__name__
            )
            
            return {
                "connection_healthy": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def validate_index(self) -> Dict[str, Any]:
        """Validate that the index exists and has the correct mapping."""
        
        try:
            # Check if index exists
            if not self.es_client.indices.exists(index=self.index_name):
                return {
                    "valid": False,
                    "error": f"Index {self.index_name} does not exist"
                }
            
            # Get index mapping
            mapping = self.es_client.indices.get_mapping(index=self.index_name)
            index_mapping = mapping[self.index_name]["mappings"]
            
            # Check for embedding field
            properties = index_mapping.get("properties", {})
            embedding_props = properties.get(self.embedding_field, {})
            
            if not embedding_props:
                return {
                    "valid": False,
                    "error": f"Embedding field '{self.embedding_field}' not found in mapping"
                }
            
            # Check vector dimension
            dimension = embedding_props.get("dims")
            expected_dimension = settings.elasticsearch.vector_dimension
            
            if dimension != expected_dimension:
                return {
                    "valid": False,
                    "error": f"Vector dimension mismatch: expected {expected_dimension}, got {dimension}"
                }
            
            return {
                "valid": True,
                "index_name": self.index_name,
                "embedding_field": self.embedding_field,
                "vector_dimension": dimension,
                "mapping_fields": list(properties.keys())
            }
            
        except Exception as e:
            self.logger.error(
                "Index validation failed",
                error=str(e),
                error_type=type(e).__name__
            )
            
            return {
                "valid": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


# =============================================================================
# Global Retriever Instance
# =============================================================================

_retriever: Optional[ElasticSearchRetriever] = None


def get_retriever() -> ElasticSearchRetriever:
    """Get the global ElasticSearch retriever instance."""
    global _retriever
    
    if _retriever is None:
        _retriever = ElasticSearchRetriever()
    
    return _retriever


def initialize_retriever() -> bool:
    """Initialize the global ElasticSearch retriever."""
    global _retriever
    
    try:
        _retriever = ElasticSearchRetriever()
        
        # Validate index
        validation = _retriever.validate_index()
        if not validation["valid"]:
            raise ValueError(f"Index validation failed: {validation['error']}")
        
        return True
        
    except Exception as e:
        logger = get_logger("rag.retriever")
        logger.error(
            "Failed to initialize retriever",
            error=str(e),
            error_type=type(e).__name__
        )
        return False


# =============================================================================
# Convenience Functions
# =============================================================================

def search_documents(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    search_type: str = "vector",
    metadata_filters: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """Convenience function to search documents."""
    retriever = get_retriever()
    return retriever.search(
        query=query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        search_type=search_type,
        metadata_filters=metadata_filters
    )


def get_retriever_health() -> Dict[str, Any]:
    """Convenience function to get retriever health status."""
    retriever = get_retriever()
    return retriever.get_health_status()


def validate_retriever_index() -> Dict[str, Any]:
    """Convenience function to validate retriever index."""
    retriever = get_retriever()
    return retriever.validate_index() 