from abc import ABC
from typing import IO, AsyncGenerator

from .page import Page


class Parser(ABC):
    """
    Abstract parser that parses PDFs into pages
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        if False:
            yield
