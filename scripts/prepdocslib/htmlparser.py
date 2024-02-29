from bs4 import BeautifulSoup
import re
from typing import IO, AsyncGenerator

from .page import Page
from .parser import Parser


def cleanup_data(data: str) -> str:
    """Cleans up the given content using regexes
    Args:
        content (str): The content to clean up.
    Returns:
        str: The cleaned up content.
    """
    output = re.sub(r"\n{2,}", "\n", data)
    output = re.sub(r"[^\S\n]{2,}", " ", output)
    output = re.sub(r"-{2,}", "--", output)

    return output.strip()

class LocalHTMLParser(Parser):
    """Parses HTML text into Page objects."""

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parses the given content.
        Args:
            content (str): The content to parse.
            file_name (str): The file name associated with the content.
        Returns:
            Document: The parsed document.
        """
        data = content.read()
        soup = BeautifulSoup(data, 'html.parser')

        # Parse the content as it is without any formatting changes
        result = soup.get_text()

        yield Page(0, 0, text=cleanup_data(result))
