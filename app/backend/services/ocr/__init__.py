"""
OCR Service Module.

Provides OCR functionality with support for multiple providers:
- Ollama (local vision models)
- Azure Document Intelligence
"""

from .base import OCRProvider, OCRResult
from .ollama_client import OllamaOCRClient
from .azure_document_intelligence_client import AzureDocumentIntelligenceOCRClient

__all__ = [
    "OCRProvider",
    "OCRResult",
    "OllamaOCRClient",
    "AzureDocumentIntelligenceOCRClient"
]





