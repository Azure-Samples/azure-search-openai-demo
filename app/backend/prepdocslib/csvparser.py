import csv
from collections.abc import AsyncGenerator
from typing import IO, Optional

from .page import Page
from .parser import Parser


class CsvParser(Parser):
    """
    Concrete parser that can parse CSV into Page objects.

    By default, each row becomes its own Page object. When ``max_chars_per_page``
    is set to a positive value, consecutive rows are grouped into a single Page
    until adding another row would exceed that character budget. Grouping avoids
    emitting one Page per row for large CSV files, which can exhaust memory in the
    cloud ingestion text-processor function.
    """

    def __init__(self, max_chars_per_page: Optional[int] = None):
        self.max_chars_per_page = max_chars_per_page

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        # Check if content is in bytes (binary file) and decode to string
        content_str: str
        if isinstance(content, (bytes, bytearray)):
            content_str = content.decode("utf-8")
        elif hasattr(content, "read"):  # Handle BufferedReader
            content_str = content.read().decode("utf-8")

        # Create a CSV reader from the text content
        reader = csv.reader(content_str.splitlines())

        # Skip the header row
        next(reader, None)

        if self.max_chars_per_page and self.max_chars_per_page > 0:
            page_num = 0
            offset = 0
            current_rows: list[str] = []
            current_length = 0
            for row in reader:
                row_text = ",".join(row)
                row_length = len(row_text) + 1  # Account for the newline used to join rows
                # Flush the current page before it would exceed the character budget.
                # A single row longer than the budget still becomes its own page.
                if current_rows and current_length + row_length > self.max_chars_per_page:
                    page_text = "\n".join(current_rows)
                    yield Page(page_num, offset, page_text)
                    offset += len(page_text) + 1
                    page_num += 1
                    current_rows = []
                    current_length = 0
                current_rows.append(row_text)
                current_length += row_length

            if current_rows:
                page_text = "\n".join(current_rows)
                yield Page(page_num, offset, page_text)
        else:
            offset = 0
            for i, row in enumerate(reader):
                page_text = ",".join(row)
                yield Page(i, offset, page_text)
                offset += len(page_text) + 1  # Account for newline character
