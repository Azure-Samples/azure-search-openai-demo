"""
OCR Service Module.

Provides OCR functionality with support for multiple providers:
- DeepSeek OCR
- Azure Document Intelligence
"""

from .base import OCRProvider, OCRResult
from .deepseek_client import DeepSeekOCRClient
from .azure_document_intelligence_client import AzureDocumentIntelligenceOCRClient

__all__ = [
    "OCRProvider",
    "OCRResult",
    "DeepSeekOCRClient",
    "AzureDocumentIntelligenceOCRClient"
]





