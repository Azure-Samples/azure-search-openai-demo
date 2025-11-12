"""
Azure Document Intelligence OCR Client.

Integration with Azure AI Document Intelligence for OCR.
"""

import io
from typing import Dict, Any, Optional
import logging
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import HttpResponseError

from .base import OCRResult, OCRProvider

logger = logging.getLogger(__name__)


class AzureDocumentIntelligenceOCRClient(OCRProvider):
    """
    Azure Document Intelligence client for OCR.
    
    Uses Azure AI Document Intelligence (formerly Form Recognizer) for text extraction.
    """
    
    def __init__(
        self,
        endpoint: str,
        credential: AsyncTokenCredential | AzureKeyCredential,
        model_id: str = "prebuilt-read",
        api_version: str = "2024-02-29-preview"
    ):
        """
        Initialize Azure Document Intelligence OCR client.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            credential: Azure credential (ManagedIdentityCredential or AzureKeyCredential)
            model_id: Model ID to use (default: prebuilt-read for OCR)
            api_version: API version to use
        """
        self.endpoint = endpoint.rstrip('/')
        self.credential = credential
        self.model_id = model_id
        self.api_version = api_version
        self._client: Optional[DocumentIntelligenceClient] = None
    
    async def _get_client(self) -> DocumentIntelligenceClient:
        """Get or create Document Intelligence client."""
        if self._client is None:
            self._client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=self.credential
            )
        return self._client
    
    async def extract_text(
        self,
        image_data: bytes,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> OCRResult:
        """
        Extract text from image using Azure Document Intelligence.
        
        Args:
            image_data: Image bytes (PNG, JPEG, PDF, etc.)
            language: Optional language hint (Azure DI supports auto-detection)
            options: Optional provider-specific options
            
        Returns:
            OCRResult with extracted text and metadata
        """
        try:
            client = await self._get_client()
            
            # Prepare analyze request
            analyze_request = AnalyzeDocumentRequest(bytes_source=image_data)
            
            # Add language hint if provided
            if language:
                analyze_request.locale = language
            
            # Start analysis
            poller = await client.begin_analyze_document(
                model_id=self.model_id,
                analyze_request=analyze_request,
                output_content_format="markdown"  # Get markdown format for better structure
            )
            
            # Wait for result
            result = await poller.result()
            
            # Extract text from all pages
            all_text = result.content or ""
            pages = []
            
            if result.pages:
                for page in result.pages:
                    page_text = ""
                    # Extract text from page
                    # Note: Azure DI returns structured content, we extract from content field
                    if result.content:
                        # For now, use full content (pages are separated in markdown)
                        # In production, you might want to parse page-by-page
                        page_text = result.content
                    
                    pages.append({
                        "page_number": page.page_number,
                        "text": page_text,
                        "width": page.width,
                        "height": page.height,
                        "unit": page.unit
                    })
            
            # Calculate confidence (Azure DI doesn't provide overall confidence)
            # Use presence of content as a proxy
            confidence = 1.0 if all_text else 0.0
            
            metadata = {
                "provider": "azure_document_intelligence",
                "model_id": self.model_id,
                "language": language or "auto",
                "api_version": self.api_version,
                "page_count": len(pages) if pages else 1
            }
            
            return OCRResult(
                text=all_text,
                confidence=confidence,
                pages=pages,
                metadata=metadata
            )
            
        except HttpResponseError as e:
            logger.error(f"Azure Document Intelligence error: {e}")
            raise Exception(f"Azure Document Intelligence error: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting text with Azure Document Intelligence: {e}")
            raise
    
    async def close(self):
        """Close the client and clean up resources."""
        if self._client:
            await self._client.close()
            self._client = None





