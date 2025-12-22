"""
Base text splitter interface.
"""

from abc import ABC
from collections.abc import Generator

from ..models import Chunk, Page


class TextSplitter(ABC):
    """
    Abstract base class for splitting pages into smaller chunks.

    Subclasses implement different chunking strategies (sentence-based,
    simple character-based, etc.)
    """

    def split_pages(self, pages: list[Page]) -> Generator[Chunk, None, None]:
        """Split pages into chunks.

        Args:
            pages: List of Page objects to split

        Yields:
            Chunk objects containing split content
        """
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield
