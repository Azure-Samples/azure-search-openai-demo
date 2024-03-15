import shutil
from pathlib import Path

import pytest

from scripts.prepdocslib.listfilestrategy import LocalListFileStrategy
from scripts.prepdocslib.pdfparser import LocalPdfParser
from scripts.prepdocslib.searchmanager import Section
from scripts.prepdocslib.textsplitter import Page, TextSplitter


def test_split_empty_pages():
    t = TextSplitter(False, True)

    assert list(t.split_pages([])) == []


def test_split_small_pages():
    t = TextSplitter(has_image_embeddings=False, verbose=True)

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text="Not a large page")]))
    assert len(split_pages) == 1
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == "Not a large page"


@pytest.mark.asyncio
async def test_list_parse_and_split(tmp_path):
    text_splitter = TextSplitter(False, True)
    pdf_parser = LocalPdfParser()
    for pdf in Path("data").glob("*.pdf"):
        shutil.copy(str(pdf.absolute()), tmp_path)

    list_file_strategy = LocalListFileStrategy(path_pattern=str(tmp_path / "*"), verbose=True)
    files = list_file_strategy.list()
    processed = 0
    async for file in files:
        pages = [page async for page in pdf_parser.parse(content=file.content)]
        assert pages
        sections = [
            Section(split_page, content=file, category="test category")
            for split_page in text_splitter.split_pages(pages)
        ]
        assert sections
        processed += 1
    assert processed > 1
