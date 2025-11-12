"""
NOMIC Embeddings Service

Supports multiple NOMIC embedding models:
- nomic-embed-text-v1.5: General text embeddings
- nomic-embed-code-v1: Code-specific embeddings
- nomic-embed-vision-v1.5: Multimodal (text + image) embeddings

Can be used via NOMIC Python SDK (local or remote) or via API endpoint.
"""

import aiohttp
import asyncio
import os
from typing import List, Optional, Literal
import logging

logger = logging.getLogger("scripts")


class NomicEmbeddings:
    """
    Class for using NOMIC embeddings.
    Supports both SDK-based (Python package) and API-based access.
    Follows the same interface pattern as OpenAIEmbeddings for seamless integration.
    """
    
    # Model dimensions (NOMIC embeddings have fixed dimensions)
    MODEL_DIMENSIONS = {
        "nomic-embed-text-v1.5": 768,
        "nomic-embed-code-v1": 768,
        "nomic-embed-vision-v1.5": 768,
    }
    
    # Default task types for different models
    DEFAULT_TASK_TYPES = {
        "nomic-embed-text-v1.5": "search_document",
        "nomic-embed-code-v1": "search_document",
        "nomic-embed-vision-v1.5": "search_document",
    }
    
    def __init__(
        self,
        model: str = "nomic-embed-text-v1.5",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        use_sdk: bool = False,
        inference_mode: Literal["local", "remote"] = "remote",
        task_type: Optional[str] = None,
        batch_size: int = 16,
        max_retries: int = 3,
    ):
        """
        Initialize NOMIC embeddings service.
        
        Args:
            model: NOMIC model name (e.g., 'nomic-embed-text-v1.5', 'nomic-embed-code-v1')
            api_key: NOMIC API key (required for remote mode or API endpoint)
            endpoint: Optional custom API endpoint URL (if using custom deployment)
            use_sdk: If True, use NOMIC Python SDK. If False, use API endpoint.
            inference_mode: 'local' or 'remote' (only used if use_sdk=True)
            task_type: Task type ('search_document', 'search_query', 'classification', 'clustering')
            batch_size: Batch size for embedding requests
            max_retries: Maximum retry attempts
        """
        self.model = model
        self.api_key = api_key.strip() if api_key else None
        self.endpoint = endpoint.rstrip('/') if endpoint else None
        self.use_sdk = use_sdk
        self.inference_mode = inference_mode
        self.task_type = task_type or self.DEFAULT_TASK_TYPES.get(model, "search_document")
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.embedding_dimensions = self.MODEL_DIMENSIONS.get(model, 768)
        
        # Validate model
        if model not in self.MODEL_DIMENSIONS:
            logger.warning(f"Unknown NOMIC model: {model}. Using default dimensions (768)")
        
        # Validate API key for remote/API mode
        if not use_sdk and not self.api_key and not self.endpoint:
            # Try to get from environment
            self.api_key = os.getenv("NOMIC_API_KEY")
            if not self.api_key:
                logger.warning("NOMIC API key not provided. Some operations may fail.")
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text."""
        embeddings = await self.create_embeddings([text])
        return embeddings[0] if embeddings else []
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of texts."""
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self._create_batch_embeddings(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def _create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts with retry logic."""
        if self.use_sdk:
            return await self._create_batch_embeddings_sdk(texts)
        else:
            return await self._create_batch_embeddings_api(texts)
    
    async def _create_batch_embeddings_sdk(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings using NOMIC Python SDK."""
        try:
            # Import NOMIC SDK (might not be installed)
            from nomic import embed
            
            # Generate embeddings
            output = embed.text(
                texts=texts,
                model=self.model,
                task_type=self.task_type,
                inference_mode=self.inference_mode,
            )
            
            embeddings = output.get('embeddings', [])
            logger.info(
                f"Computed NOMIC embeddings (SDK) in batch. Batch size: {len(texts)}, Model: {self.model}"
            )
            return embeddings
            
        except ImportError:
            logger.error("NOMIC SDK not installed. Install with: pip install nomic")
            raise Exception("NOMIC SDK not available. Install with: pip install nomic")
        except Exception as e:
            logger.error(f"NOMIC SDK embedding error: {e}")
            raise
    
    async def _create_batch_embeddings_api(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings using NOMIC API endpoint."""
        # Determine API endpoint
        if self.endpoint:
            api_url = f"{self.endpoint}/v1/embeddings"
        else:
            # Default NOMIC API endpoint
            api_url = "https://api-atlas.nomic.ai/v1/embeddings"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        payload = {
            'model': self.model,
            'texts': texts,
            'task_type': self.task_type,
        }
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=120)  # Longer timeout for embeddings
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(
                                f"Computed NOMIC embeddings (API) in batch. Batch size: {len(texts)}, Model: {self.model}"
                            )
                            
                            # Handle different response formats
                            if 'embeddings' in result:
                                return result['embeddings']
                            elif 'data' in result:
                                # OpenAI-compatible format
                                return [item['embedding'] for item in result['data']]
                            else:
                                logger.error(f"Unexpected NOMIC API response format: {result.keys()}")
                                raise Exception("Unexpected NOMIC API response format")
                        else:
                            error_text = await response.text()
                            logger.error(f"NOMIC API error {response.status}: {error_text}")
                            if attempt == self.max_retries - 1:
                                raise Exception(f"NOMIC API failed after {self.max_retries} attempts: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"NOMIC API timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise Exception("NOMIC service timeout")
                    
            except Exception as e:
                logger.error(f"NOMIC embedding error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                
            # Wait before retry (exponential backoff)
            await asyncio.sleep(2 ** attempt)
        
        raise Exception("NOMIC embedding generation failed")
    
    def get_embedding_dimensions(self) -> int:
        """Return the dimension size of embeddings."""
        return self.embedding_dimensions
    
    @property
    def open_ai_dimensions(self) -> int:
        """Compatibility property for OpenAIEmbeddings interface."""
        return self.embedding_dimensions


# Convenience functions for creating NOMIC embeddings instances
def create_nomic_text_embeddings(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    use_sdk: bool = False,
) -> NomicEmbeddings:
    """Create NOMIC text embeddings instance."""
    return NomicEmbeddings(
        model="nomic-embed-text-v1.5",
        api_key=api_key,
        endpoint=endpoint,
        use_sdk=use_sdk,
    )


def create_nomic_code_embeddings(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    use_sdk: bool = False,
) -> NomicEmbeddings:
    """Create NOMIC code embeddings instance."""
    return NomicEmbeddings(
        model="nomic-embed-code-v1",
        api_key=api_key,
        endpoint=endpoint,
        use_sdk=use_sdk,
    )


def create_nomic_vision_embeddings(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    use_sdk: bool = False,
) -> NomicEmbeddings:
    """Create NOMIC vision (multimodal) embeddings instance."""
    return NomicEmbeddings(
        model="nomic-embed-vision-v1.5",
        api_key=api_key,
        endpoint=endpoint,
        use_sdk=use_sdk,
    )





