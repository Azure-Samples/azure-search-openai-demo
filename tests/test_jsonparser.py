import io

import pytest

from scripts.prepdocslib.jsonparser import JsonParser


@pytest.mark.asyncio
async def test_jsonparser_single_obj():
    file = io.StringIO('{"test": "test"}')
    file.name = "test.json"
    jsonparser = JsonParser()
    pages = [page async for page in jsonparser.parse(file)]
    assert len(pages) == 1


@pytest.mark.asyncio
async def test_jsonparser_array_multiple_obj():
    file = io.StringIO('[{"test": "test"},{"test": "test"}]')
    file.name = "test.json"
    jsonparser = JsonParser()
    pages = [page async for page in jsonparser.parse(file)]
    assert len(pages) == 2
