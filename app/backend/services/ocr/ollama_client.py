"""
Ollama OCR Client.

Integration with local Ollama server for text extraction from images.
Ollama provides OpenAI-compatible API for vision models.
"""

import aiohttp
import base64
from typing import Dict, Any, Optional
import logging

from .base import OCRResult, OCRProvider

logger = logging.getLogger(__name__)


class OllamaOCRClient(OCRProvider):
    """
    Ollama OCR client for text extraction from images using local Ollama server.
    
    Supports any Ollama vision model (e.g., llava, bakllava, deepseek-v2).
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llava",
        timeout: int = 120
    ):
        """
        Initialize Ollama OCR client.
        
        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434/v1)
            model: Model name for OCR (default: llava)
            timeout: Request timeout in seconds (default: 120 for local processing)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        
    async def extract_text(
        self,
        image_data: bytes,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> OCRResult:
        """
        Extract text from image using Ollama vision model.
        
        Args:
            image_data: Image bytes (PNG, JPEG, PDF, etc.)
            language: Optional language hint (e.g., 'en', 'zh', 'ja')
            options: Optional provider-specific options
            
        Returns:
            OCRResult with extracted text and metadata
        """
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request payload (OpenAI-compatible format)
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Extract all text from this image. Return only the extracted text, preserving formatting and structure."
                            }
                        ]
                    }
                ],
                "stream": False,
                "max_tokens": 4096
            }
            
            # Add language hint if provided
            if language:
                payload["messages"][0]["content"][1]["text"] += f" (Language: {language})"
            
            # Add custom options if provided
            if options:
                if "temperature" in options:
                    payload["temperature"] = options["temperature"]
                if "max_tokens" in options:
                    payload["max_tokens"] = options["max_tokens"]
            
            # Make API request (Ollama uses OpenAI-compatible API, no auth needed)
            headers = {
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama OCR API error {response.status}: {error_text}")
                        raise Exception(f"Ollama OCR API error {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    # Extract text from response
                    if "choices" in data and len(data["choices"]) > 0:
                        extracted_text = data["choices"][0]["message"]["content"]
                        
                        # Extract confidence if available
                        confidence = 1.0
                        if "usage" in data:
                            # Use token counts as a proxy for confidence
                            total_tokens = data["usage"].get("total_tokens", 0)
                            if total_tokens > 0:
                                # Normalize confidence (heuristic)
                                confidence = min(1.0, total_tokens / 1000.0)
                        
                        metadata = {
                            "provider": "ollama",
                            "model": self.model,
                            "language": language,
                            "base_url": self.base_url,
                            "usage": data.get("usage", {})
                        }
                        
                        return OCRResult(
                            text=extracted_text,
                            confidence=confidence,
                            pages=[],  # Ollama doesn't provide page-level results
                            metadata=metadata
                        )
                    else:
                        raise Exception("No text extracted from Ollama OCR response")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Ollama OCR network error: {e}")
            raise Exception(f"Ollama OCR network error: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama OCR error: {e}")
            raise
    
    async def extract_text_from_url(
        self,
        image_url: str,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> OCRResult:
        """
        Extract text from image URL using Ollama OCR.
        
        Args:
            image_url: URL of the image to process
            language: Optional language hint
            options: Optional provider-specific options
            
        Returns:
            OCRResult with extracted text and metadata
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch image from URL: {response.status}")
                    image_data = await response.read()
                    return await self.extract_text(image_data, language, options)
        except Exception as e:
            logger.error(f"Error fetching image from URL: {e}")
            raise

