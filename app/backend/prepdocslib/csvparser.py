import csv
from typing import IO, AsyncGenerator

from .page import Page
from .parser import Parser


class CsvParser(Parser):
    """
    Concrete parser that can parse CSV into Page objects. Each row becomes a Page object.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        # Check if content is in bytes (binary file) and decode to string
        content_str: str
        if isinstance(content, (bytes, bytearray)):
            content_str = content.decode("utf-8")
        elif hasattr(content, "read"):  # Handle BufferedReader
            content_str = content.read().decode("utf-8")

        # Create a CSV reader from the text content
        reader = csv.reader(content_str.splitlines())
        offset = 0

        # Skip the header row
        next(reader, None)

        for i, row in enumerate(reader):
            page_text = ",".join(row)
            yield Page(i, offset, page_text)
            offset += len(page_text) + 1  # Account for newline character
