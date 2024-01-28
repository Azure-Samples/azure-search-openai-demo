import json
from abc import ABC
from typing import IO, AsyncGenerator, Union
from .page import Page

from .strategy import USER_AGENT

class JsonFileParser():
    """
    Concrete parser that can parse json into pages
    """

    def parse(self, content: IO):
        offset = 0
        data = json.loads(content.read())
        if isinstance(data, list):
            for i, obj in enumerate(data):
                page_text = json.dumps(data[i])
                offset += len(page_text)
                yield Page(i, offset, page_text)
        elif isinstance(data, dict):
            yield Page(1, 0, json.dumps(data))
