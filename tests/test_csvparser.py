import io

import pytest

from prepdocslib.csvparser import CsvParser  # Adjust import to the correct module


@pytest.mark.asyncio
async def test_csvparser_single_row():
    # Mock CSV content with a single row in binary format
    file = io.BytesIO(b"col1,col2,col3\nvalue1,value2,value3")
    file.name = "test.csv"
    csvparser = CsvParser()

    # Parse the file
    pages = [page async for page in csvparser.parse(file)]

    # Assertions
    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "value1,value2,value3"


@pytest.mark.asyncio
async def test_csvparser_multiple_rows():
    # Mock CSV content with multiple rows in binary format
    file = io.BytesIO(b"col1,col2,col3\nvalue1,value2,value3\nvalue4,value5,value6")
    file.name = "test.csv"
    csvparser = CsvParser()

    # Parse the file
    pages = [page async for page in csvparser.parse(file)]

    # Assertions
    assert len(pages) == 2  # Expect only data rows, skipping the header
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "value1,value2,value3"

    assert pages[1].page_num == 1
    assert pages[1].offset == len(pages[0].text) + 1  # Length of the first row plus a newline
    assert pages[1].text == "value4,value5,value6"


@pytest.mark.asyncio
async def test_csvparser_empty_file():
    # Mock empty CSV content in binary format
    file = io.BytesIO(b"")
    file.name = "test.csv"
    csvparser = CsvParser()

    # Parse the file
    pages = [page async for page in csvparser.parse(file)]

    # Assertions
    assert len(pages) == 0  # No rows should be parsed from an empty file
