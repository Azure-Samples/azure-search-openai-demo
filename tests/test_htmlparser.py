import io

import pytest

from scripts.prepdocslib.htmlparser import LocalHTMLParser


@pytest.mark.asyncio
async def test_htmlparser_single_obj():
    file = io.StringIO(
        """
                       <html>
                       <title>Test title</title>
                        <body>
                            <h1>Test header</h1>
                            <p>Test paragraph</p>
                        </body>
                       </html>
                       """
    )
    file.name = "test.json"
    htmlparser = LocalHTMLParser()
    pages = [page async for page in htmlparser.parse(file)]
    print(pages[0].text)
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Test title\nTest header\nTest paragraph"
