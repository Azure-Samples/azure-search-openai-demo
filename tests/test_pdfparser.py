import io
import json
import logging
import math
import pathlib
from unittest.mock import AsyncMock, MagicMock, Mock

import pymupdf
import pytest
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeResult,
    BoundingRegion,
    DocumentCaption,
    DocumentFigure,
    DocumentPage,
    DocumentSpan,
    DocumentTable,
    DocumentTableCell,
)
from azure.core.exceptions import HttpResponseError
from PIL import Image, ImageChops

from prepdocslib.mediadescriber import ContentUnderstandingDescriber
from prepdocslib.pdfparser import DocumentAnalysisParser

from .mocks import MockAzureCredential

TEST_DATA_DIR = pathlib.Path(__file__).parent / "test-data"


def assert_image_equal(image1, image2):
    assert image1.size == image2.size
    assert image1.mode == image2.mode
    # Based on https://stackoverflow.com/a/55251080/1347623
    diff = ImageChops.difference(image1, image2).histogram()
    sq = (value * (i % 256) ** 2 for i, value in enumerate(diff))
    rms = math.sqrt(sum(sq) / float(image1.size[0] * image1.size[1]))
    assert rms < 90


def test_crop_image_from_pdf_page():
    doc = pymupdf.open(TEST_DATA_DIR / "Financial Market Analysis Report 2023.pdf", filetype="pdf")
    page_number = 2
    bounding_box = (1.4703, 2.8371, 5.5381, 6.6022)  # Coordinates in inches

    cropped_image_bytes = DocumentAnalysisParser.crop_image_from_pdf_page(doc, page_number, bounding_box)

    # Verify the output is not empty
    assert cropped_image_bytes is not None
    assert len(cropped_image_bytes) > 0

    # Verify the output is a valid image
    cropped_image = Image.open(io.BytesIO(cropped_image_bytes))
    assert cropped_image.format == "PNG"
    assert cropped_image.size[0] > 0
    assert cropped_image.size[1] > 0

    expected_image = Image.open(TEST_DATA_DIR / "Financial Market Analysis Report 2023_page2_figure.png")
    assert_image_equal(cropped_image, expected_image)


def test_table_to_html():
    table = DocumentTable(
        row_count=2,
        column_count=2,
        cells=[
            DocumentTableCell(row_index=0, column_index=0, content="Header 1", kind="columnHeader"),
            DocumentTableCell(row_index=0, column_index=1, content="Header 2", kind="columnHeader"),
            DocumentTableCell(row_index=1, column_index=0, content="Cell 1"),
            DocumentTableCell(row_index=1, column_index=1, content="Cell 2"),
        ],
    )

    expected_html = (
        "<figure><table>"
        "<tr><th>Header 1</th><th>Header 2</th></tr>"
        "<tr><td>Cell 1</td><td>Cell 2</td></tr>"
        "</table></figure>"
    )

    result_html = DocumentAnalysisParser.table_to_html(table)
    assert result_html == expected_html


def test_table_to_html_with_spans():
    table = DocumentTable(
        row_count=2,
        column_count=2,
        cells=[
            DocumentTableCell(row_index=0, column_index=0, content="Header 1", kind="columnHeader", column_span=2),
            DocumentTableCell(row_index=1, column_index=0, content="Cell 1", row_span=2),
            DocumentTableCell(row_index=1, column_index=1, content="Cell 2"),
        ],
    )

    expected_html = (
        "<figure><table>"
        "<tr><th colSpan=2>Header 1</th></tr>"
        "<tr><td rowSpan=2>Cell 1</td><td>Cell 2</td></tr>"
        "</table></figure>"
    )

    result_html = DocumentAnalysisParser.table_to_html(table)
    assert result_html == expected_html


@pytest.mark.asyncio
async def test_figure_to_html_without_bounding_regions():
    doc = MagicMock()
    figure = DocumentFigure(id="1", caption=None, bounding_regions=None)
    cu_describer = MagicMock()

    result_html = await DocumentAnalysisParser.figure_to_html(doc, figure, cu_describer)
    expected_html = "<figure><figcaption></figcaption></figure>"

    assert result_html == expected_html


@pytest.mark.asyncio
async def test_figure_to_html_with_bounding_regions(monkeypatch, caplog):
    doc = MagicMock()
    figure = DocumentFigure(
        id="1",
        caption=DocumentCaption(content="Figure 1"),
        bounding_regions=[
            BoundingRegion(page_number=1, polygon=[1.4703, 2.8371, 5.5409, 2.8415, 5.5381, 6.6022, 1.4681, 6.5978]),
            BoundingRegion(page_number=2, polygon=[1.4703, 2.8371, 5.5409, 2.8415, 5.5381, 6.6022, 1.4681, 6.5978]),
        ],
    )
    cu_describer = AsyncMock()

    async def mock_describe_image(image_bytes):
        assert image_bytes == b"image_bytes"
        return "Described Image"

    monkeypatch.setattr(cu_describer, "describe_image", mock_describe_image)

    def mock_crop_image_from_pdf_page(doc, page_number, bounding_box) -> bytes:
        assert page_number == 0
        assert bounding_box == (1.4703, 2.8371, 5.5381, 6.6022)
        return b"image_bytes"

    monkeypatch.setattr(DocumentAnalysisParser, "crop_image_from_pdf_page", mock_crop_image_from_pdf_page)

    with caplog.at_level(logging.WARNING):
        result_html = await DocumentAnalysisParser.figure_to_html(doc, figure, cu_describer)
        expected_html = "<figure><figcaption>Figure 1<br>Described Image</figcaption></figure>"
        assert result_html == expected_html
        assert "Figure 1 has more than one bounding region, using the first one" in caplog.text


@pytest.mark.asyncio
async def test_parse_simple(monkeypatch):
    mock_poller = MagicMock()

    async def mock_begin_analyze_document(self, model_id, analyze_request, **kwargs):
        return mock_poller

    async def mock_poller_result():
        return AnalyzeResult(
            content="Page content",
            pages=[DocumentPage(page_number=1, spans=[DocumentSpan(offset=0, length=12)])],
            tables=[],
            figures=[],
        )

    monkeypatch.setattr(DocumentIntelligenceClient, "begin_analyze_document", mock_begin_analyze_document)
    monkeypatch.setattr(mock_poller, "result", mock_poller_result)

    parser = DocumentAnalysisParser(
        endpoint="https://example.com", credential=MockAzureCredential(), use_content_understanding=False
    )
    content = io.BytesIO(b"pdf content bytes")
    content.name = "test.pdf"
    pages = [page async for page in parser.parse(content)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Page content"


@pytest.mark.asyncio
async def test_parse_doc_with_tables(monkeypatch):
    mock_poller = MagicMock()

    async def mock_begin_analyze_document(self, model_id, analyze_request, **kwargs):
        return mock_poller

    async def mock_poller_result():
        content = open(TEST_DATA_DIR / "Simple Table_content.txt").read()
        return AnalyzeResult(
            content=content,
            pages=[DocumentPage(page_number=1, spans=[DocumentSpan(offset=0, length=172)])],
            tables=[
                DocumentTable(
                    bounding_regions=[
                        BoundingRegion(
                            page_number=1, polygon=[0.4394, 1.0459, 4.2509, 1.0449, 4.2524, 1.9423, 0.4408, 1.9432]
                        )
                    ],
                    row_count=3,
                    column_count=2,
                    cells=[
                        DocumentTableCell(
                            row_index=0,
                            column_index=0,
                            content="Header 1",
                            kind="columnHeader",
                            spans=[DocumentSpan(offset=39, length=8)],
                        ),
                        DocumentTableCell(
                            row_index=0,
                            column_index=1,
                            content="Header 2",
                            kind="columnHeader",
                            spans=[DocumentSpan(offset=57, length=8)],
                        ),
                        DocumentTableCell(
                            row_index=1, column_index=0, content="Cell 1", spans=[DocumentSpan(offset=86, length=6)]
                        ),
                        DocumentTableCell(
                            row_index=1, column_index=1, content="Cell 2", spans=[DocumentSpan(offset=102, length=6)]
                        ),
                        DocumentTableCell(
                            row_index=2, column_index=0, content="Cell 3", spans=[DocumentSpan(offset=129, length=6)]
                        ),
                        DocumentTableCell(
                            row_index=2, column_index=1, content="Cell 4", spans=[DocumentSpan(offset=145, length=6)]
                        ),
                    ],
                    spans=[DocumentSpan(offset=22, length=149)],
                )
            ],
            figures=[],
        )

    monkeypatch.setattr(DocumentIntelligenceClient, "begin_analyze_document", mock_begin_analyze_document)
    monkeypatch.setattr(mock_poller, "result", mock_poller_result)

    parser = DocumentAnalysisParser(
        endpoint="https://example.com", credential=MockAzureCredential(), use_content_understanding=False
    )
    with open(TEST_DATA_DIR / "Simple Table.pdf", "rb") as f:
        content = io.BytesIO(f.read())
        content.name = "Simple Table.pdf"
    pages = [page async for page in parser.parse(content)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert (
        pages[0].text
        == "# Simple HTML Table\n\n\n<figure><table><tr><th>Header 1</th><th>Header 2</th></tr><tr><td>Cell 1</td><td>Cell 2</td></tr><tr><td>Cell 3</td><td>Cell 4</td></tr></table></figure>"
    )


@pytest.mark.asyncio
async def test_parse_doc_with_figures(monkeypatch):
    mock_poller = MagicMock()

    async def mock_begin_analyze_document(self, model_id, analyze_request, **kwargs):
        return mock_poller

    async def mock_poller_result():
        content = open(TEST_DATA_DIR / "Simple Figure_content.txt").read()
        return AnalyzeResult(
            content=content,
            pages=[DocumentPage(page_number=1, spans=[DocumentSpan(offset=0, length=148)])],
            figures=[
                DocumentFigure(
                    id="1.1",
                    caption=DocumentCaption(content="Figure 1"),
                    bounding_regions=[
                        BoundingRegion(
                            page_number=1, polygon=[0.4295, 1.3072, 1.7071, 1.3076, 1.7067, 2.6088, 0.4291, 2.6085]
                        )
                    ],
                    spans=[DocumentSpan(offset=70, length=22)],
                )
            ],
        )

    monkeypatch.setattr(DocumentIntelligenceClient, "begin_analyze_document", mock_begin_analyze_document)
    monkeypatch.setattr(mock_poller, "result", mock_poller_result)

    async def mock_describe_image(self, image_bytes):
        return "Pie chart"

    monkeypatch.setattr(ContentUnderstandingDescriber, "describe_image", mock_describe_image)

    parser = DocumentAnalysisParser(
        endpoint="https://example.com",
        credential=MockAzureCredential(),
        use_content_understanding=True,
        content_understanding_endpoint="https://example.com",
    )

    with open(TEST_DATA_DIR / "Simple Figure.pdf", "rb") as f:
        content = io.BytesIO(f.read())
        content.name = "Simple Figure.pdf"

    pages = [page async for page in parser.parse(content)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert (
        pages[0].text
        == "# Simple Figure\n\nThis text is before the figure and NOT part of it.\n\n\n<figure><figcaption>Figure 1<br>Pie chart</figcaption></figure>\n\n\nThis is text after the figure that's not part of it."
    )


@pytest.mark.asyncio
async def test_parse_unsupportedformat(monkeypatch, caplog):
    mock_poller = MagicMock()

    async def mock_begin_analyze_document(self, model_id, analyze_request, **kwargs):

        if kwargs.get("features") == ["ocrHighResolution"]:

            class FakeErrorOne:
                def __init__(self):
                    self.error = Mock(message="A fake error", code="FakeErrorOne")

            class FakeHttpResponse(HttpResponseError):
                def __init__(self, response, error, *args, **kwargs):
                    self.error = error
                    super().__init__(self, response=response, *args, **kwargs)

            message = {
                "error": {
                    "code": "InvalidArgument",
                    "message": "A fake error",
                }
            }
            response = Mock(status_code=500, headers={})
            response.text = lambda encoding=None: json.dumps(message).encode("utf-8")
            response.headers["content-type"] = "application/json"
            response.content_type = "application/json"
            raise FakeHttpResponse(response, FakeErrorOne())
        else:
            return mock_poller

    async def mock_poller_result():
        return AnalyzeResult(
            content="Page content",
            pages=[DocumentPage(page_number=1, spans=[DocumentSpan(offset=0, length=12)])],
            tables=[],
            figures=[],
        )

    monkeypatch.setattr(DocumentIntelligenceClient, "begin_analyze_document", mock_begin_analyze_document)
    monkeypatch.setattr(mock_poller, "result", mock_poller_result)

    parser = DocumentAnalysisParser(
        endpoint="https://example.com",
        credential=MockAzureCredential(),
        use_content_understanding=True,
        content_understanding_endpoint="https://example.com",
    )
    content = io.BytesIO(b"pdf content bytes")
    content.name = "test.docx"
    with caplog.at_level(logging.ERROR):
        pages = [page async for page in parser.parse(content)]
        assert "This document type does not support media description." in caplog.text

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Page content"
