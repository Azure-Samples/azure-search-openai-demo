import json
import shutil
from pathlib import Path

import pytest
import tiktoken

from scripts.prepdocslib.listfilestrategy import LocalListFileStrategy
from scripts.prepdocslib.page import Page
from scripts.prepdocslib.pdfparser import LocalPdfParser
from scripts.prepdocslib.searchmanager import Section
from scripts.prepdocslib.textsplitter import (
    ENCODING_MODEL,
    SentenceTextSplitter,
    SimpleTextSplitter,
)


def test_sentencetextsplitter_split_empty_pages():
    t = SentenceTextSplitter(has_image_embeddings=False)

    assert list(t.split_pages([])) == []


def test_sentencetextsplitter_split_small_pages():
    t = SentenceTextSplitter(has_image_embeddings=False)

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text="Not a large page")]))
    assert len(split_pages) == 1
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == "Not a large page"


@pytest.mark.asyncio
async def test_sentencetextsplitter_list_parse_and_split(tmp_path, snapshot):
    text_splitter = SentenceTextSplitter(has_image_embeddings=False)
    pdf_parser = LocalPdfParser()
    for pdf in Path("data").glob("*.pdf"):
        shutil.copy(str(pdf.absolute()), tmp_path)

    list_file_strategy = LocalListFileStrategy(path_pattern=str(tmp_path / "*"))
    files = list_file_strategy.list()
    processed = 0
    results = {}
    async for file in files:
        pages = [page async for page in pdf_parser.parse(content=file.content)]
        assert pages
        sections = [
            Section(split_page, content=file, category="test category")
            for split_page in text_splitter.split_pages(pages)
        ]
        assert sections
        results[file.filename()] = [section.split_page.text for section in sections]
        processed += 1
    assert processed > 1
    # Sort results by key
    results = {k: results[k] for k in sorted(results)}
    snapshot.assert_match(json.dumps(results, indent=2), "text_splitter_sections.txt")


def test_simpletextsplitter_split_empty_pages():
    t = SimpleTextSplitter()

    assert list(t.split_pages([])) == []


def test_simpletextsplitter_split_small_pages():
    t = SimpleTextSplitter()

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(split_pages) == 1
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == '{"test": "Not a large page"}'


def test_sentencetextsplitter_split_pages():
    max_object_length = 10
    t = SimpleTextSplitter(max_object_length=max_object_length)

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(split_pages) == 3
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == '{"test": "'
    assert len(split_pages[0].text) <= max_object_length
    assert split_pages[1].page_num == 1
    assert split_pages[1].text == "Not a larg"
    assert len(split_pages[1].text) <= max_object_length
    assert split_pages[2].page_num == 2
    assert split_pages[2].text == 'e page"}'
    assert len(split_pages[2].text) <= max_object_length


def pytest_generate_tests(metafunc):
    """Parametrize the test_doc fixture with all the pdf files in the test-data directory."""
    if "test_doc" in metafunc.fixturenames:
        metafunc.parametrize("test_doc", [pdf for pdf in Path("tests", "test-data").glob("*.pdf")])


@pytest.mark.asyncio
async def test_sentencetextsplitter_multilang(test_doc, tmp_path):
    text_splitter = SentenceTextSplitter(has_image_embeddings=False)
    bpe = tiktoken.encoding_for_model(ENCODING_MODEL)
    pdf_parser = LocalPdfParser()

    shutil.copy(str(test_doc.absolute()), tmp_path)

    list_file_strategy = LocalListFileStrategy(path_pattern=str(tmp_path / "*"))
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

        # Verify the size of the sections
        token_lengths = []
        for section in sections:
            assert section.split_page.text != ""
            assert len(section.split_page.text) <= (text_splitter.max_section_length * 1.2)
            # Verify the number of tokens is below 500
            token_lengths.append((len(bpe.encode(section.split_page.text)), len(section.split_page.text)))
        # verify that none of the numbers in token_lengths are above 500
        assert all([tok_len <= text_splitter.max_tokens_per_section for tok_len, _ in token_lengths]), (
            test_doc.name,
            token_lengths,
        )
    assert processed == 1


def test_split_tables():
    t = SentenceTextSplitter(has_image_embeddings=False)

    test_text_without_table = """Contoso Electronics is a leader in the aerospace industry, providing advanced electronic
components for both commercial and military aircraft. We specialize in creating cutting-
edge systems that are both reliable and efficient. Our mission is to provide the highest
quality aircraft components to our customers, while maintaining a commitment to safety
and excellence. We are proud to have built a strong reputation in the aerospace industry
and strive to continually improve our products and services. Our experienced team of
engineers and technicians are dedicated to providing the best products and services to our
customers. With our commitment to excellence, we are sure to remain a leader in the
aerospace industry for years to come. At Contoso Electronics, we strive to ensure our employees are getting the feedback they
need to continue growing and developing in their roles. We understand that performance
reviews are a key part of this process and it is important to us that they are conducted in an
effective and efficient manner <fable> Performance reviews are conducted annually and are an important part of your career
development. During the review, your supervisor will discuss your performance over the
past year and provide feedback on areas for improvement. They will also provide you with
an opportunity to discuss your goals and objectives for the upcoming year.
</table>
 """
    test_text_with_table = test_text_without_table.replace("<fable>", "<table>")

    split_pages_with_table = list(t.split_pages(pages=[Page(page_num=0, offset=0, text=test_text_with_table)]))
    split_pages_without_table = list(t.split_pages(pages=[Page(page_num=0, offset=0, text=test_text_without_table)]))

    assert len(split_pages_with_table) == 2

    assert split_pages_with_table[0].text != split_pages_without_table[0].text

    # The table algorithm should move the start of the second section to include the table start
    # but only in the test text that has a table tag..
    assert "<table" in split_pages_with_table[0].text
    assert "<table" in split_pages_with_table[1].text
    assert split_pages_with_table[1].text != split_pages_without_table[1].text
