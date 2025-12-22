"""
File processor that combines a parser with a text splitter.
"""

from dataclasses import dataclass

from .base import Parser
from ..splitters.base import TextSplitter


@dataclass(frozen=True)
class FileProcessor:
    """Combines a parser and splitter for processing a specific file type.

    Attributes:
        parser: Parser to extract text from the file
        splitter: Splitter to chunk the extracted text
    """
    parser: Parser
    splitter: TextSplitter
