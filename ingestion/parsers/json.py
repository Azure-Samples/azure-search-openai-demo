"""
JSON document parser.
"""

import json
from collections.abc import AsyncGenerator
from typing import IO

from ..models import Page
from .base import Parser


class JsonParser(Parser):
    """
    Concrete parser that can parse JSON into Page objects.
    A top-level object becomes a single Page, while a top-level array
    becomes multiple Page objects.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parse JSON content into Page objects.

        Args:
            content: File-like object containing JSON data

        Yields:
            Page objects containing JSON data
        """
        offset = 0
        data = json.loads(content.read())
        if isinstance(data, list):
            for i, obj in enumerate(data):
                offset += 1  # For opening bracket or comma before object
                page_text = json.dumps(obj)
                yield Page(page_num=i, offset=offset, text=page_text)
                offset += len(page_text)
        elif isinstance(data, dict):
            yield Page(page_num=0, offset=0, text=json.dumps(data))
