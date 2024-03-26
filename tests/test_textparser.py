import io

import pytest

from prepdocslib.textparser import TextParser


@pytest.mark.asyncio
async def test_textparser_remove_new_lines():
    file = io.BytesIO(
        b"""
        # Text Example with multiple empty lines
        this is paragraph 1



        and this is paragraph 2
        """
    )
    parser = TextParser()
    pages = [page async for page in parser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "# Text Example with multiple empty lines\n this is paragraph 1\n and this is paragraph 2"


@pytest.mark.asyncio
async def test_textparser_remove_white_spaces():
    file = io.BytesIO(b"              Test multiple  white spaces                  ")
    parser = TextParser()
    pages = [page async for page in parser.parse(file)]
    assert pages[0].text == "Test multiple white spaces"


@pytest.mark.asyncio
async def test_textparser_full():
    file = io.BytesIO(
        b"""
        # Text  Example
        Some short text here, with bullets:
        * write code
        * test code
        * merge code


        ## Subheading
        Some more text here with a link to Azure.  Here's a the link to [Azure](https://azure.microsoft.com/).
        """
    )
    file.name = "test.md"
    parser = TextParser()
    pages = [page async for page in parser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert (
        pages[0].text
        == "# Text Example\n Some short text here, with bullets:\n * write code\n * test code\n * merge code\n ## Subheading\n Some more text here with a link to Azure. Here's a the link to [Azure](https://azure.microsoft.com/)."
    )
