import io

import pytest

from prepdocslib.jsonparser import JsonParser


@pytest.mark.asyncio
async def test_jsonparser_single_obj():
    file = io.StringIO('{"test": "test"}')
    file.name = "test.json"
    jsonparser = JsonParser()
    pages = [page async for page in jsonparser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == '{"test": "test"}'


@pytest.mark.asyncio
async def test_jsonparser_array_multiple_obj():
    file = io.StringIO('[{"test1": "test"},{"test2": "test"}]')
    file.name = "test.json"
    jsonparser = JsonParser()
    pages = [page async for page in jsonparser.parse(file)]
    assert len(pages) == 2
    assert pages[0].page_num == 0
    assert pages[0].offset == 1
    assert pages[0].text == '{"test1": "test"}'
    assert pages[1].page_num == 1
    assert pages[1].offset == 19
    assert pages[1].text == '{"test2": "test"}'
