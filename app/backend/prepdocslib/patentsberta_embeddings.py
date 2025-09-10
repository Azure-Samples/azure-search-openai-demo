import aiohttp
import asyncio
from typing import List, Optional
import logging

logger = logging.getLogger("scripts")

class PatentsBertaEmbeddings:
    """
    Class for using PatentsBERTa embeddings from a custom FastAPI service
    Follows the same interface pattern as OpenAIEmbeddings for seamless integration
    """
    
    def __init__(
        self, 
        endpoint: str, 
        api_key: Optional[str] = None,
        batch_size: int = 16,
        max_retries: int = 3
    ):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.embedding_dimensions = 768  # PatentsBERTa dimension size
        
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of texts using PatentsBERTa service"""
        all_embeddings = []
        
        # Process in batches to avoid overwhelming the service
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self._create_batch_embeddings(batch)
            all_embeddings.extend(batch_embeddings)
            
        return all_embeddings
    
    async def _create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts with retry logic"""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            
        payload = {
            'texts': texts,
            'normalize': True
        }
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.endpoint}/embeddings",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(
                                "Computed PatentsBERTa embeddings in batch. Batch size: %d",
                                len(texts)
                            )
                            return result['embeddings']
                        else:
                            error_text = await response.text()
                            logger.error(f"PatentsBERTa API error: {response.status} - {error_text}")
                            if attempt == self.max_retries - 1:
                                raise Exception(f"PatentsBERTa API failed after {self.max_retries} attempts")
                            
            except asyncio.TimeoutError:
                logger.warning(f"PatentsBERTa timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise Exception("PatentsBERTa service timeout")
                    
            except Exception as e:
                logger.error(f"PatentsBERTa embedding error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                    
            # Wait before retry
            await asyncio.sleep(2 ** attempt)
            
        raise Exception("PatentsBERTa embedding generation failed")

    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text"""
        embeddings = await self.create_embeddings([text])
        return embeddings[0] if embeddings else []

    def get_embedding_dimensions(self) -> int:
        """Return the dimension size of embeddings"""
        return self.embedding_dimensions
