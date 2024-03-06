import io

import pytest

from scripts.prepdocslib.markdownparser import MarkdownParser


@pytest.mark.asyncio
async def test_markdownparser_remove_new_lines():
    file = io.BytesIO(
        b"""
        # Markdown Example with multiple empty lines
        this is paragraph 1

        

        and this is paragraph 2
        """
    )
    parser = MarkdownParser()
    pages = [page async for page in parser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert (
        pages[0].text
        == "# Markdown Example with multiple empty lines\n this is paragraph 1\n \n and this is paragraph 2"
    )


@pytest.mark.asyncio
async def test_markdownparser_remove_white_spaces():
    file = io.BytesIO(b"              Test multiple  white spaces                  ")
    parser = MarkdownParser()
    pages = [page async for page in parser.parse(file)]
    assert pages[0].text == "Test multiple white spaces"


@pytest.mark.asyncio
async def test_markdownparser_full():
    file = io.BytesIO(
        b"""
        # Markdown  Example
        Some short text here, with bullets:
        * write code
        * test code
        * merge code


        ## Subheading
        Some more text here with a link to Azure.  Here's a the linked to [Azure](https://azure.microsoft.com/).
        """
    )
    file.name = "test.md"
    parser = MarkdownParser()
    pages = [page async for page in parser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert (
        pages[0].text
        == "# Markdown Example\n Some short text here, with bullets:\n * write code\n * test code\n * merge code\n ## Subheading\n Some more text here with a link to Azure. Here's a the linked to [Azure](https://azure.microsoft.com/)."
    )
