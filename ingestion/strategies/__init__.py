"""
Ingestion strategies module.

This module provides different strategies for ingesting documents into Azure AI Search.
"""

from .base import DocumentAction, Strategy
from .file import FileStrategy, UploadUserFileStrategy
from .integrated import IntegratedVectorizerStrategy
from .cloud import CloudIngestionStrategy

__all__ = [
    "DocumentAction",
    "Strategy",
    "FileStrategy",
    "UploadUserFileStrategy",
    "IntegratedVectorizerStrategy",
    "CloudIngestionStrategy",
]
