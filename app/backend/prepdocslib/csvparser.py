import csv
from typing import IO, AsyncGenerator
from .page import Page
from .parser import Parser


class CsvParser(Parser):
    """
    Concrete parser that can parse CSV into Page objects. Each row becomes a Page object.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        # Ensure the file is read in text mode
        text_content = content.read().decode('utf-8')  # Decode bytes to string if opened in binary mode
        reader = csv.reader(text_content.splitlines())  # Create CSV reader from text lines
        offset = 0
        for i, row in enumerate(reader):
            page_text = ",".join(row)  # Combine CSV row elements back to a string
            yield Page(i, offset, page_text)
            offset += len(page_text) + 1  # Add 1 for the newline character or comma
