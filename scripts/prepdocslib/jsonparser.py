import json
from typing import IO
from .page import Page

class JsonParser():
    """
    Concrete parser that can parse json into pages
    """

    def parse(self, content: IO):
        offset = 0
        data = json.loads(content.read())
        if isinstance(data, list):
            for i, obj in enumerate(data):
                page_text = json.dumps(obj)
                offset += len(page_text)
                yield Page(i, offset, page_text)
        elif isinstance(data, dict):
            yield Page(1, 0, json.dumps(data))
