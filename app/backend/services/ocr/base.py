"""
Base OCR Provider Protocol.

Defines the interface for OCR providers (Ollama, Azure Document Intelligence, etc.).
"""

from typing import Protocol, Dict, Any, Optional
from io import BytesIO


class OCRResult:
    """Standardized OCR result structure."""
    
    def __init__(
        self,
        text: str,
        confidence: float = 1.0,
        pages: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize OCR result.
        
        Args:
            text: Extracted text content
            confidence: Overall confidence score (0.0 to 1.0)
            pages: List of page-level results with page numbers and text
            metadata: Additional metadata (provider, language, etc.)
        """
        self.text = text
        self.confidence = confidence
        self.pages = pages or []
        self.metadata = metadata or {}


class OCRProvider(Protocol):
    """Protocol for OCR providers."""
    
    async def extract_text(
        self,
        image_data: bytes,
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> OCRResult:
        """
        Extract text from image using OCR.
        
        Args:
            image_data: Image bytes (PNG, JPEG, PDF, etc.)
            language: Optional language hint (e.g., 'en', 'zh', 'ja')
            options: Optional provider-specific options
            
        Returns:
            OCRResult with extracted text and metadata
        """
        ...





