"""
Base strategy classes for document ingestion.

This module provides the abstract Strategy class and DocumentAction enum
that all ingestion strategies inherit from.
"""

from abc import ABC
from enum import Enum


class DocumentAction(Enum):
    """Actions that can be performed on documents during ingestion."""
    Add = 0
    Remove = 1
    RemoveAll = 2


class Strategy(ABC):
    """
    Abstract strategy for ingesting documents into a search service.
    
    It has a single setup step to perform any required initialization,
    and then a run step that actually ingests documents into the search service.
    """

    async def setup(self):
        """Perform any required initialization (e.g., create index)."""
        raise NotImplementedError

    async def run(self):
        """Execute the ingestion strategy."""
        raise NotImplementedError
