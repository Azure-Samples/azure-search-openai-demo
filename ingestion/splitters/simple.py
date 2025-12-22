"""
Simple character-based text splitter.
"""

from collections.abc import Generator

from ..models import Chunk, Page
from .base import TextSplitter


class SimpleTextSplitter(TextSplitter):
    """
    Splits pages into smaller chunks based on a max object length.
    It is not aware of the content of the page - just splits at character boundaries.
    """

    def __init__(self, max_object_length: int = 1000):
        """Initialize the simple splitter.

        Args:
            max_object_length: Maximum characters per chunk
        """
        self.max_object_length = max_object_length

    def split_pages(self, pages: list[Page]) -> Generator[Chunk, None, None]:
        """Split all pages into fixed-size chunks.

        Args:
            pages: List of pages to split

        Yields:
            Chunk objects of max_object_length characters
        """
        all_text = "".join(page.text for page in pages)
        if len(all_text.strip()) == 0:
            return

        length = len(all_text)
        if length <= self.max_object_length:
            yield Chunk(page_num=0, text=all_text)
            return

        # Split into fixed-size chunks
        for i in range(0, length, self.max_object_length):
            yield Chunk(page_num=i // self.max_object_length, text=all_text[i : i + self.max_object_length])
