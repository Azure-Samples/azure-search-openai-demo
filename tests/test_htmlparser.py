import io

import pytest

from scripts.prepdocslib.htmlparser import LocalHTMLParser


@pytest.mark.asyncio
async def test_htmlparser_remove_new_lines():
    file = io.StringIO("<p><br><br><br><br><br>Test multiple new lines<br><br><br><br><br></p>")
    file.name = "test.json"
    htmlparser = LocalHTMLParser()
    pages = [page async for page in htmlparser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Test multiple new lines"


@pytest.mark.asyncio
async def test_htmlparser_remove_white_spaces():
    file = io.StringIO("<p>              Test multiple white spaces                   </p>")
    file.name = "test.json"
    htmlparser = LocalHTMLParser()
    pages = [page async for page in htmlparser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Test multiple white spaces"


@pytest.mark.asyncio
async def test_htmlparser_remove_hyphens():
    file = io.StringIO("<p>--- --------  --------   ----- Test hyphens ----------- --------- -----  ----</p>")
    file.name = "test.json"
    htmlparser = LocalHTMLParser()
    pages = [page async for page in htmlparser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "-- -- -- -- Test hyphens -- -- -- --"


@pytest.mark.asyncio
async def test_htmlparser_full():
    file = io.StringIO(
        """
        <html>
            <head>
                <title>Test title</title>
            </head>
            <body>
                <!-- Test comment -->
                <h1>Test header</h1>
                <p>
                Test paragraph one<br>
                Test paragraph two<br><br>
                Test paragraph three<br><br><br>
                </p>
                <p>
                ---------- Test hyphens ----------
                </p>
            </body>
        </html>
        """
    )
    file.name = "test.json"
    htmlparser = LocalHTMLParser()
    pages = [page async for page in htmlparser.parse(file)]
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert (
        pages[0].text
        == "Test title\nTest header\n Test paragraph one\n Test paragraph two\n Test paragraph three\n -- Test hyphens --"
    )
