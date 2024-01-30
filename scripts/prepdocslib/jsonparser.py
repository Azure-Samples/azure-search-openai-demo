import json
from typing import IO, AsyncGenerator

from .page import Page
from .parser import Parser


class JsonParser(Parser):
    """
    Concrete parser that can parse json into pages
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        offset = 0
        data = json.loads(content.read())
        if isinstance(data, list):
            for i, obj in enumerate(data):
                page_text = json.dumps(obj)
                offset += len(page_text)
                yield Page(i, offset, page_text)
        elif isinstance(data, dict):
            yield Page(0, 0, json.dumps(data))
