"""
Embeddings module for text and image embedding generation.
"""

from .text import OpenAIEmbeddings
from .image import ImageEmbeddings

__all__ = ["OpenAIEmbeddings", "ImageEmbeddings"]
