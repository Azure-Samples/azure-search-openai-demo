from abc import ABC
from typing import IO, AsyncGenerator

from .page import Page


class Parser(ABC):
    """
    Abstract parser that parses content into Page objects
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        if False:
            yield  # pragma: no cover - this is necessary for mypy to type check
