"""
HTML document parser.
"""

import logging
import re
from collections.abc import AsyncGenerator
from typing import IO

from bs4 import BeautifulSoup

from ..models import Page
from .base import Parser

logger = logging.getLogger("ingestion")


def cleanup_data(data: str) -> str:
    """Cleans up the given content using regexes.

    Args:
        data: The data to clean up.

    Returns:
        The cleaned up data.
    """
    # match two or more newlines and replace them with one new line
    output = re.sub(r"\n{2,}", "\n", data)
    # match two or more spaces that are not newlines and replace them with one space
    output = re.sub(r"[^\S\n]{2,}", " ", output)
    # match two or more hyphens and replace them with two hyphens
    output = re.sub(r"-{2,}", "--", output)
    return output.strip()


class LocalHTMLParser(Parser):
    """Parses HTML text into Page objects using BeautifulSoup."""

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parses the given HTML content.

        To learn more, please visit https://pypi.org/project/beautifulsoup4/

        Args:
            content: The HTML content to parse.

        Yields:
            Page with extracted text content.
        """
        logger.info("Extracting text from '%s' using local HTML parser (BeautifulSoup)", content.name)

        data = content.read()
        soup = BeautifulSoup(data, "html.parser")

        # Get text only from html file
        result = soup.get_text()

        yield Page(page_num=0, offset=0, text=cleanup_data(result))
