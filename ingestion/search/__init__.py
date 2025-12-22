"""
Search module for Azure AI Search operations.
"""

from .client import SearchInfo
from .index_manager import SearchManager

__all__ = ["SearchInfo", "SearchManager"]
