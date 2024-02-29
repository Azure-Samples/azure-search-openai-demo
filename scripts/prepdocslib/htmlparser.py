import re
from typing import IO, AsyncGenerator

from bs4 import BeautifulSoup

from .page import Page
from .parser import Parser


def cleanup_data(data: str) -> str:
    """Cleans up the given content using regexes
    Args:
        data: (str): The data to clean up.
    Returns:
        str: The cleaned up data.
    """
    output = re.sub(r"\n{2,}", "\n", data)
    output = re.sub(r"[^\S\n]{2,}", " ", output)
    output = re.sub(r"-{2,}", "--", output)

    return output.strip()


class LocalHTMLParser(Parser):
    """Parses HTML text into Page objects."""

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parses the given content.
        To learn more, please visit https://pypi.org/project/beautifulsoup4/
        Args:
            content (IO): The content to parse.
        Returns:
            Page: The parsed html Page.
        """
        data = content.read()
        soup = BeautifulSoup(data, "html.parser")

        # Get text only from html file
        result = soup.get_text()

        yield Page(0, 0, text=cleanup_data(result))
