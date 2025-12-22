"""
Base parser interface for document parsing.
"""

from abc import ABC
from collections.abc import AsyncGenerator
from typing import IO

from ..models import Page


class Parser(ABC):
    """
    Abstract parser that parses content into Page objects.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parse the content and yield Page objects.

        Args:
            content: File-like object to parse

        Yields:
            Page objects containing parsed content
        """
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield
