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


@pytest.mark.asyncio
async def test_csvparser_groups_rows_when_max_chars_set():
    # Three short data rows; with a generous budget they all land on one page
    file = io.BytesIO(b"col1,col2,col3\nv1,v2,v3\nv4,v5,v6\nv7,v8,v9")
    file.name = "test.csv"
    csvparser = CsvParser(max_chars_per_page=100)

    pages = [page async for page in csvparser.parse(file)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "v1,v2,v3\nv4,v5,v6\nv7,v8,v9"


@pytest.mark.asyncio
async def test_csvparser_splits_when_budget_exceeded():
    # Each data row is 8 chars + 1 newline = 9; a budget of 12 fits one row per page
    file = io.BytesIO(b"col1,col2,col3\nv1,v2,v3\nv4,v5,v6\nv7,v8,v9")
    file.name = "test.csv"
    csvparser = CsvParser(max_chars_per_page=12)

    pages = [page async for page in csvparser.parse(file)]

    assert len(pages) == 3
    assert [page.text for page in pages] == ["v1,v2,v3", "v4,v5,v6", "v7,v8,v9"]
    assert [page.page_num for page in pages] == [0, 1, 2]
    # Offsets advance by len(text) + 1 for the joining newline
    assert pages[0].offset == 0
    assert pages[1].offset == len(pages[0].text) + 1
    assert pages[2].offset == pages[1].offset + len(pages[1].text) + 1


@pytest.mark.asyncio
async def test_csvparser_oversized_single_row_becomes_own_page():
    # A single row larger than the budget must still be emitted (not dropped or looped)
    long_value = "x" * 50
    file = io.BytesIO(f"col1\nshort\n{long_value}\nshort2".encode())
    file.name = "test.csv"
    csvparser = CsvParser(max_chars_per_page=10)

    pages = [page async for page in csvparser.parse(file)]

    assert [page.text for page in pages] == ["short", long_value, "short2"]


@pytest.mark.asyncio
async def test_csvparser_large_file_does_not_explode_into_per_row_pages():
    # Regression for OOM: many rows must collapse into far fewer grouped pages
    rows = "\n".join(f"row{i},value{i}" for i in range(1000))
    file = io.BytesIO(f"col1,col2\n{rows}".encode())
    file.name = "test.csv"
    csvparser = CsvParser(max_chars_per_page=2000)

    pages = [page async for page in csvparser.parse(file)]

    # Without grouping this would be 1000 pages; grouping keeps it small
    assert len(pages) < 50

