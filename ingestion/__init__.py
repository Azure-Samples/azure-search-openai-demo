"""
Standalone document ingestion module for Azure AI Search.

This module provides a decoupled, reusable library for ingesting documents
into Azure AI Search with support for:
- Multiple file formats (PDF, HTML, text, CSV, JSON, etc.)
- Document parsing and chunking
- Embedding generation (text and image)
- Azure AI Search index creation and management
- Multiple ingestion strategies (local, integrated vectorization, cloud)

Example usage:
    from ingestion import IngestionConfig, upload_and_index
    from ingestion.strategies import FileStrategy

    config = IngestionConfig.from_env()
    result = await upload_and_index(files="data/*", config=config)
"""

from ingestion.config import IngestionConfig, OpenAIHost
from ingestion.models import Chunk, File, ImageOnPage, Page, Section
from ingestion.uploader import upload_and_index, build_file_processors, setup_figure_processor

# Re-export key classes for convenience
from ingestion.search.client import SearchInfo
from ingestion.search.index_manager import SearchManager
from ingestion.storage.blob import AdlsBlobManager, BaseBlobManager, BlobManager
from ingestion.embeddings.text import OpenAIEmbeddings
from ingestion.embeddings.image import ImageEmbeddings
from ingestion.strategies.base import DocumentAction, Strategy
from ingestion.strategies.file import FileStrategy, UploadUserFileStrategy, parse_file
from ingestion.strategies.integrated import IntegratedVectorizerStrategy
from ingestion.strategies.cloud import CloudIngestionStrategy
from ingestion.parsers import (
    Parser, FileProcessor, LocalPdfParser, DocumentAnalysisParser,
    LocalHTMLParser, TextParser, CsvParser, JsonParser,
)
from ingestion.splitters import TextSplitter, SentenceTextSplitter, SimpleTextSplitter
from ingestion.figures import FigureProcessor, MediaDescriptionStrategy, build_figure_markup

__all__ = [
    # Configuration
    "IngestionConfig",
    "OpenAIHost",
    # Models
    "File",
    "Page",
    "Chunk",
    "Section",
    "ImageOnPage",
    # High-level API
    "upload_and_index",
    "build_file_processors",
    "setup_figure_processor",
    "parse_file",
    # Search
    "SearchInfo",
    "SearchManager",
    # Storage
    "BlobManager",
    "AdlsBlobManager",
    "BaseBlobManager",
    # Embeddings
    "OpenAIEmbeddings",
    "ImageEmbeddings",
    # Strategies
    "DocumentAction",
    "Strategy",
    "FileStrategy",
    "UploadUserFileStrategy",
    "IntegratedVectorizerStrategy",
    "CloudIngestionStrategy",
    # Parsers
    "Parser",
    "FileProcessor",
    "LocalPdfParser",
    "DocumentAnalysisParser",
    "LocalHTMLParser",
    "TextParser",
    "CsvParser",
    "JsonParser",
    # Splitters
    "TextSplitter",
    "SentenceTextSplitter",
    "SimpleTextSplitter",
    # Figures
    "FigureProcessor",
    "MediaDescriptionStrategy",
    "build_figure_markup",
]
