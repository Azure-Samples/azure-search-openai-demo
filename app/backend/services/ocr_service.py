"""
OCR Service.

Main service for OCR operations with provider abstraction.
Supports multiple OCR providers (Ollama, Azure Document Intelligence, etc.).
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
import os

from services.ocr.base import OCRResult, OCRProvider
from services.ocr.ollama_client import OllamaOCRClient
from services.ocr.azure_document_intelligence_client import AzureDocumentIntelligenceOCRClient
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from config import OCR_PROVIDER, OCR_ON_INGEST

logger = logging.getLogger(__name__)


class OCRProviderType(str, Enum):
    """Supported OCR providers."""
    OLLAMA = "ollama"
    AZURE_DOCUMENT_INTELLIGENCE = "azure_document_intelligence"
    NONE = "none"  # Disabled


class OCRService:
    """
    OCR Service with provider abstraction.
    
    Supports multiple OCR providers and can switch between them.
    """
    
    def __init__(
        self,
        provider: Optional[OCRProviderType] = None,
        provider_client: Optional[OCRProvider] = None,
        enable_on_ingest: Optional[bool] = None
    ):
        """
        Initialize OCR service.
        
        Args:
            provider: OCR provider type (defaults to OCR_PROVIDER env var)
            provider_client: Pre-initialized OCR provider client (optional)
            enable_on_ingest: Whether to run OCR during document ingestion (defaults to OCR_ON_INGEST env var)
        """
        # Use environment variables if not provided
        if provider is None:
            provider_str = OCR_PROVIDER
            try:
                provider = OCRProviderType(provider_str)
            except ValueError:
                logger.warning(f"Invalid OCR_PROVIDER: {provider_str}, defaulting to NONE")
                provider = OCRProviderType.NONE
        
        if enable_on_ingest is None:
            enable_on_ingest = OCR_ON_INGEST
        
        self.provider = provider
        self.provider_client = provider_client
        self.enable_on_ingest = enable_on_ingest
        
        if provider_client is None and provider != OCRProviderType.NONE:
            self.provider_client = self._create_provider_client(provider)
    
    def _create_provider_client(self, provider: OCRProviderType) -> Optional[OCRProvider]:
        """
        Create OCR provider client based on provider type.
        
        Args:
            provider: Provider type to create
            
        Returns:
            OCRProvider instance or None if disabled
        """
        if provider == OCRProviderType.NONE:
            return None
        
        elif provider == OCRProviderType.OLLAMA:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            model = os.getenv("OLLAMA_OCR_MODEL", "llava")
            timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
            
            logger.info(f"Initializing Ollama OCR client: {base_url}, model: {model}")
            return OllamaOCRClient(
                base_url=base_url,
                model=model,
                timeout=timeout
            )
        
        elif provider == OCRProviderType.AZURE_DOCUMENT_INTELLIGENCE:
            endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            if not endpoint:
                logger.warning("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT not set, OCR service disabled")
                return None
            
            # Try to get credential
            # For now, use key-based auth (can be enhanced with Managed Identity)
            key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            if key:
                credential = AzureKeyCredential(key)
            else:
                # Try to use Managed Identity (requires async credential)
                # This would need to be passed in from the app setup
                logger.warning("AZURE_DOCUMENT_INTELLIGENCE_KEY not set, cannot create client")
                return None
            
            model_id = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", "prebuilt-read")
            
            # Note: Azure Document Intelligence client is async, but we're storing it
            # The actual usage will need to handle async context
            # For now, return None and handle in async context
            logger.warning("Azure Document Intelligence client requires async context, use create_async_client()")
            return None
        
        else:
            logger.warning(f"Unknown OCR provider: {provider}")
            return None
    
    async def create_async_client(
        self,
        provider: OCRProviderType,
        azure_credential: Optional[AsyncTokenCredential] = None
    ) -> Optional[OCRProvider]:
        """
        Create async OCR provider client (for Azure Document Intelligence).
        
        Args:
            provider: Provider type
            azure_credential: Azure credential for Managed Identity auth
            
        Returns:
            OCRProvider instance or None
        """
        if provider == OCRProviderType.AZURE_DOCUMENT_INTELLIGENCE:
            endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            if not endpoint:
                logger.warning("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT not set")
                return None
            
            credential = azure_credential
            if not credential:
                key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
                if key:
                    from azure.core.credentials import AzureKeyCredential
                    credential = AzureKeyCredential(key)
                else:
                    logger.warning("AZURE_DOCUMENT_INTELLIGENCE_KEY not set and no credential provided")
                    return None
            
            model_id = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", "prebuilt-read")
            
            return AzureDocumentIntelligenceOCRClient(
                endpoint=endpoint,
                credential=credential,
                model_id=model_id
            )
        
        return None
    
    async def extract_text(
        self,
        image_data: bytes,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[OCRResult]:
        """
        Extract text from image using configured OCR provider.
        
        Args:
            image_data: Image bytes to process
            language: Optional language hint
            options: Optional provider-specific options
            
        Returns:
            OCRResult with extracted text, or None if OCR is disabled
        """
        if self.provider == OCRProviderType.NONE or self.provider_client is None:
            logger.debug("OCR service is disabled")
            return None
        
        try:
            result = await self.provider_client.extract_text(
                image_data=image_data,
                language=language,
                options=options
            )
            logger.info(f"OCR extracted {len(result.text)} characters with {result.confidence:.2f} confidence")
            return result
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None
    
    async def extract_text_from_url(
        self,
        image_url: str,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[OCRResult]:
        """
        Extract text from image URL using configured OCR provider.
        
        Args:
            image_url: URL of image to process
            language: Optional language hint
            options: Optional provider-specific options
            
        Returns:
            OCRResult with extracted text, or None if OCR is disabled
        """
        if self.provider == OCRProviderType.NONE or self.provider_client is None:
            return None
        
        if isinstance(self.provider_client, OllamaOCRClient):
            try:
                result = await self.provider_client.extract_text_from_url(
                    image_url=image_url,
                    language=language,
                    options=options
                )
                return result
            except Exception as e:
                logger.error(f"OCR extraction from URL failed: {e}")
                return None
        else:
            # For other providers, fetch image first
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            logger.error(f"Failed to fetch image from URL: {response.status}")
                            return None
                        image_data = await response.read()
                        return await self.extract_text(image_data, language, options)
            except Exception as e:
                logger.error(f"Error fetching image from URL: {e}")
                return None
    
    def is_enabled(self) -> bool:
        """Check if OCR service is enabled."""
        return self.provider != OCRProviderType.NONE and self.provider_client is not None

