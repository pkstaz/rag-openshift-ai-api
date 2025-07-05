import time
import logging
from typing import List, Optional, Union, Dict, Any
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from ..config.settings import settings
from ..utils.metrics import track_embedding_generation, record_error


# =============================================================================
# Embedding Manager Class
# =============================================================================

class EmbeddingManager:
    """Manages sentence transformer embeddings with consistency and performance optimization."""
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """Initialize the embedding manager."""
        
        self.model_name = model_name or settings.embedding.model_name
        self.device = device or settings.embedding.device
        self.model: Optional[SentenceTransformer] = None
        self.vector_dimension = settings.elasticsearch.vector_dimension
        self.batch_size = settings.embedding.batch_size
        self.normalize_embeddings = settings.embedding.normalize_embeddings
        
        # Performance tracking
        self.model_loaded = False
        self.total_embeddings_generated = 0
        self.total_processing_time = 0.0
        
        logging.info("=" * 60)
        logging.info("🔄 INITIALIZING EMBEDDING MANAGER")
        logging.info("=" * 60)
        logging.info(f"📋 Model Name: {self.model_name}")
        logging.info(f"📋 Device: {self.device}")
        logging.info(f"📋 Vector Dimension: {self.vector_dimension}")
        logging.info(f"📋 Batch Size: {self.batch_size}")
        logging.info("=" * 60)
    
    def initialize_model(self) -> bool:
        """Initialize and load the sentence transformer model."""
        
        try:
            logging.info("=" * 60)
            logging.info("🔄 LOADING SENTENCE TRANSFORMER MODEL")
            logging.info("=" * 60)
            logging.info(f"📋 Model Name: {self.model_name}")
            logging.info("=" * 60)
            
            # Load the model
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            
            # Validate model dimensions
            if not self._validate_model_dimensions():
                raise ValueError(f"Model dimensions don't match expected {self.vector_dimension}")
            
            # Warm up the model
            self._warm_up_model()
            
            self.model_loaded = True
            logging.info("=" * 60)
            logging.info("✅ MODEL LOADED SUCCESSFULLY")
            logging.info("=" * 60)
            logging.info(f"📋 Model Name: {self.model_name}")
            logging.info(f"📋 Device: {self.device}")
            logging.info(f"📋 Vector Dimension: {self.vector_dimension}")
            logging.info("=" * 60)
            
            return True
            
        except Exception as e:
            logging.error("=" * 80)
            logging.error("🚨 EMBEDDING MODEL LOAD ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Model Name: {self.model_name}")
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Verify that the embedding model is available")
            logging.error("   🔍 Check internet connection for model download")
            logging.error("   🔍 Ensure sufficient disk space")
            logging.error("   🔍 Verify device availability (CPU/GPU)")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 80)
            record_error(type(e).__name__, "embeddings")
            return False
    
    def _validate_model_dimensions(self) -> bool:
        """Validate that the model produces the expected vector dimensions."""
        
        if self.model is None:
            return False
        
        try:
            # Test with a simple sentence
            test_text = "This is a test sentence for dimension validation."
            test_embedding = self.model.encode([test_text], convert_to_numpy=True)
            
            actual_dimension = test_embedding.shape[1]
            expected_dimension = self.vector_dimension
            
            logging.info("=" * 50)
            logging.info("🔍 MODEL DIMENSION VALIDATION")
            logging.info("=" * 50)
            logging.info(f"📋 Expected Dimension: {expected_dimension}")
            logging.info(f"📋 Actual Dimension: {actual_dimension}")
            logging.info("=" * 50)
            
            return actual_dimension == expected_dimension
            
        except Exception as e:
            logging.error("=" * 80)
            logging.error("🚨 DIMENSION VALIDATION ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Expected Dimension: {self.vector_dimension}")
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Verify model configuration matches expected dimensions")
            logging.error("   🔍 Check if model is compatible with current settings")
            logging.error("   🔍 Verify model file integrity")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 80)
            return False
    
    def _warm_up_model(self) -> None:
        """Warm up the model with a few sample embeddings."""
        
        try:
            warm_up_texts = [
                "This is a warm-up sentence for the embedding model.",
                "Another warm-up sentence to optimize performance.",
                "Final warm-up sentence for model optimization."
            ]
            
            logging.info("=" * 50)
            logging.info("🔥 MODEL WARM-UP STARTED")
            logging.info("=" * 50)
            logging.info(f"📋 Number of Texts: {len(warm_up_texts)}")
            logging.info("=" * 50)
            
            # Generate embeddings for warm-up
            embeddings = self.model.encode(
                warm_up_texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=self.normalize_embeddings
            )
            
            logging.info("=" * 50)
            logging.info("✅ MODEL WARM-UP COMPLETED")
            logging.info("=" * 50)
            logging.info(f"📋 Number of Embeddings: {len(embeddings)}")
            logging.info(f"📋 Embedding Shape: {embeddings.shape}")
            logging.info("=" * 50)
            
        except Exception as e:
            logging.warning("=" * 60)
            logging.warning("⚠️ MODEL WARM-UP WARNING")
            logging.warning("=" * 60)
            logging.warning(f"📋 Model Name: {self.model_name}")
            logging.warning(f"📋 Error Type: {type(e).__name__}")
            logging.warning(f"📋 Error Message: {str(e)}")
            logging.warning("")
            logging.warning("💡 NOTE: Model warm-up failed, but model may still work")
            logging.warning("=" * 60)
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for consistency with the ingestion pipeline."""
        
        if not text:
            return ""
        
        # Basic text preprocessing (same as ingestion pipeline)
        processed_text = text.strip()
        
        # Remove extra whitespace
        processed_text = " ".join(processed_text.split())
        
        # Truncate if too long (model has limits)
        max_length = 512  # SentenceTransformer default
        if len(processed_text) > max_length:
            processed_text = processed_text[:max_length]
            logging.debug(f"Text truncated, original_length={len(text)}, truncated_length={max_length}")
        
        return processed_text
    
    def embed_query(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for a single query text."""
        
        if not self.model_loaded or self.model is None:
            logging.error("Model not loaded, cannot generate embeddings")
            return None
        
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            if not processed_text:
                logging.warning("Empty text after preprocessing")
                return None
            
            # Generate embedding with performance tracking
            with track_embedding_generation(self.model_name):
                start_time = time.time()
                
                embedding = self.model.encode(
                    [processed_text],
                    batch_size=1,
                    convert_to_numpy=True,
                    normalize_embeddings=self.normalize_embeddings
                )
                
                processing_time = time.time() - start_time
                
                # Update performance metrics
                self.total_embeddings_generated += 1
                self.total_processing_time += processing_time
            
            logging.debug(f"Query embedding generated, text_length={len(processed_text)}, embedding_shape={embedding.shape}, processing_time={processing_time}")
            
            return embedding[0]  # Return single embedding
            
        except Exception as e:
            logging.error("=" * 80)
            logging.error("🚨 QUERY EMBEDDING GENERATION ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Text Length: {len(text)}")
            logging.error(f"📋 Model Name: {self.model_name}")
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Verify that the embedding model is loaded")
            logging.error("   🔍 Check if the input text is valid")
            logging.error("   🔍 Verify model memory availability")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 80)
            record_error(type(e).__name__, "embeddings")
            return None
    
    def embed_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings for a batch of texts."""
        
        if not self.model_loaded or self.model is None:
            logging.error("Model not loaded, cannot generate embeddings")
            return None
        
        if not texts:
            logging.warning("Empty text list provided")
            return None
        
        try:
            # Preprocess all texts
            processed_texts = [self.preprocess_text(text) for text in texts]
            processed_texts = [text for text in processed_texts if text]  # Remove empty texts
            
            if not processed_texts:
                logging.warning("No valid texts after preprocessing")
                return None
            
            # Generate embeddings with performance tracking
            with track_embedding_generation(self.model_name):
                start_time = time.time()
                
                embeddings = self.model.encode(
                    processed_texts,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=self.normalize_embeddings
                )
                
                processing_time = time.time() - start_time
                
                # Update performance metrics
                self.total_embeddings_generated += len(processed_texts)
                self.total_processing_time += processing_time
            
            logging.debug(f"Batch embeddings generated, num_texts={len(processed_texts)}, embedding_shape={embeddings.shape}, processing_time={processing_time}")
            
            return embeddings
            
        except Exception as e:
            logging.error("=" * 80)
            logging.error("🚨 BATCH EMBEDDING GENERATION ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Number of Texts: {len(texts)}")
            logging.error(f"📋 Model Name: {self.model_name}")
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Verify that the embedding model is loaded")
            logging.error("   🔍 Check if the input texts are valid")
            logging.error("   🔍 Verify batch size configuration")
            logging.error("   🔍 Check available memory for batch processing")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 80)
            record_error(type(e).__name__, "embeddings")
            return None
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        
        try:
            similarity = cos_sim(embedding1, embedding2).item()
            return float(similarity)
            
        except Exception as e:
            logging.error("=" * 60)
            logging.error("🚨 SIMILARITY COMPUTATION ERROR")
            logging.error("=" * 60)
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Verify embedding dimensions match")
            logging.error("   🔍 Check if embeddings are valid numpy arrays")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 60)
            return 0.0
    
    def validate_consistency(self) -> Dict[str, Any]:
        """Validate consistency with the ingestion pipeline."""
        
        validation_results = {
            "model_loaded": self.model_loaded,
            "model_name": self.model_name,
            "device": self.device,
            "vector_dimension": self.vector_dimension,
            "batch_size": self.batch_size,
            "normalize_embeddings": self.normalize_embeddings,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
        
        try:
            # Test 1: Model dimensions
            if self.model_loaded and self.model is not None:
                test_embedding = self.embed_query("Test sentence for consistency validation.")
                if test_embedding is not None and test_embedding.shape[0] == self.vector_dimension:
                    validation_results["tests_passed"] += 1
                else:
                    validation_results["tests_failed"] += 1
                    validation_results["errors"].append("Dimension mismatch")
            
            # Test 2: Preprocessing consistency
            test_text = "  This   is   a   test   with   extra   spaces  "
            processed = self.preprocess_text(test_text)
            expected = "This is a test with extra spaces"
            if processed == expected:
                validation_results["tests_passed"] += 1
            else:
                validation_results["tests_failed"] += 1
                validation_results["errors"].append("Preprocessing inconsistency")
            
            # Test 3: Similarity computation
            if self.model_loaded:
                emb1 = self.embed_query("Hello world")
                emb2 = self.embed_query("Hello world")
                if emb1 is not None and emb2 is not None:
                    similarity = self.compute_similarity(emb1, emb2)
                    if 0.9 <= similarity <= 1.0:  # Should be very similar
                        validation_results["tests_passed"] += 1
                    else:
                        validation_results["tests_failed"] += 1
                        validation_results["errors"].append("Similarity computation issue")
            
            logging.info("=" * 60)
            logging.info("✅ CONSISTENCY VALIDATION COMPLETED")
            logging.info("=" * 60)
            logging.info(f"📋 Tests Passed: {validation_results['tests_passed']}")
            logging.info(f"📋 Tests Failed: {validation_results['tests_failed']}")
            logging.info(f"📋 Errors: {validation_results['errors']}")
            logging.info("=" * 60)
            
        except Exception as e:
            validation_results["tests_failed"] += 1
            validation_results["errors"].append(f"Validation error: {str(e)}")
            logging.error("=" * 80)
            logging.error("🚨 EMBEDDING CONSISTENCY VALIDATION ERROR")
            logging.error("=" * 80)
            logging.error(f"📋 Model Name: {self.model_name}")
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Verify model is properly loaded")
            logging.error("   🔍 Check model configuration consistency")
            logging.error("   🔍 Verify preprocessing pipeline")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 80)
        
        return validation_results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the embedding manager."""
        
        return {
            "model_loaded": self.model_loaded,
            "model_name": self.model_name,
            "device": self.device,
            "vector_dimension": self.vector_dimension,
            "total_embeddings_generated": self.total_embeddings_generated,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": (
                self.total_processing_time / self.total_embeddings_generated 
                if self.total_embeddings_generated > 0 else 0.0
            ),
            "memory_usage": self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information."""
        
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup(self) -> None:
        """Clean up resources."""
        
        try:
            if self.model is not None:
                # Clear model from memory
                del self.model
                self.model = None
            
            self.model_loaded = False
            logging.info("=" * 50)
            logging.info("🧹 EMBEDDING MANAGER CLEANED UP")
            logging.info("=" * 50)
            
        except Exception as e:
            logging.error("=" * 60)
            logging.error("🚨 EMBEDDING CLEANUP ERROR")
            logging.error("=" * 60)
            logging.error(f"📋 Error Type: {type(e).__name__}")
            logging.error(f"📋 Error Message: {str(e)}")
            logging.error("")
            logging.error("🔧 TROUBLESHOOTING STEPS:")
            logging.error("   🔍 Check if model is properly loaded")
            logging.error("   🔍 Verify memory cleanup process")
            logging.error("")
            logging.error("📊 TECHNICAL DETAILS:")
            logging.error(f"   Exception Type: {type(e).__name__}")
            logging.error(f"   Full Error: {str(e)}")
            logging.error("=" * 60)


# =============================================================================
# Global Embedding Manager Instance
# =============================================================================

_embedding_manager: Optional[EmbeddingManager] = None


def get_embedding_manager() -> EmbeddingManager:
    """Get the global embedding manager instance."""
    global _embedding_manager
    
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
        if not _embedding_manager.initialize_model():
            raise RuntimeError("Failed to initialize embedding manager")
    
    return _embedding_manager


def initialize_embeddings() -> bool:
    """Initialize the global embedding manager."""
    global _embedding_manager
    
    try:
        _embedding_manager = EmbeddingManager()
        return _embedding_manager.initialize_model()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error("=" * 80)
        logger.error("🚨 EMBEDDING INITIALIZATION ERROR")
        logger.error("=" * 80)
        logger.error(f"📋 Error Type: {type(e).__name__}")
        logger.error(f"📋 Error Message: {str(e)}")
        logger.error("")
        logger.error("🔧 TROUBLESHOOTING STEPS:")
        logger.error("   🔍 Verify that the embedding model is available")
        logger.error("   🔍 Check internet connection for model download")
        logger.error("   🔍 Ensure sufficient disk space")
        logger.error("   🔍 Verify device availability (CPU/GPU)")
        logger.error("")
        logger.error("📊 TECHNICAL DETAILS:")
        logger.error(f"   Exception Type: {type(e).__name__}")
        logger.error(f"   Full Error: {str(e)}")
        logger.error("=" * 80)
        return False


def cleanup_embeddings() -> None:
    """Clean up the global embedding manager."""
    global _embedding_manager
    
    if _embedding_manager is not None:
        _embedding_manager.cleanup()
        _embedding_manager = None


# =============================================================================
# Convenience Functions
# =============================================================================

def embed_query(text: str) -> Optional[np.ndarray]:
    """Convenience function to embed a single query."""
    manager = get_embedding_manager()
    return manager.embed_query(text)


def embed_batch(texts: List[str]) -> Optional[np.ndarray]:
    """Convenience function to embed a batch of texts."""
    manager = get_embedding_manager()
    return manager.embed_batch(texts)


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Convenience function to compute similarity between embeddings."""
    manager = get_embedding_manager()
    return manager.compute_similarity(embedding1, embedding2)


def validate_embedding_consistency() -> Dict[str, Any]:
    """Convenience function to validate embedding consistency."""
    manager = get_embedding_manager()
    return manager.validate_consistency()


def get_embedding_health() -> Dict[str, Any]:
    """Convenience function to get embedding health status."""
    manager = get_embedding_manager()
    return manager.get_health_status() 