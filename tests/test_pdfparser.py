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
    AnalyzeDocumentRequest,
    AnalyzeResult,
    BoundingRegion,
    DocumentCaption,
    DocumentFigure,
    DocumentPage,
    DocumentSpan,
    DocumentTable,
    DocumentTableCell,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from PIL import Image, ImageChops
from werkzeug.datastructures import FileStorage

from prepdocslib.figureprocessor import (
    FigureProcessor,
    MediaDescriptionStrategy,
    build_figure_markup,
    process_page_image,
)
from prepdocslib.page import ImageOnPage
from prepdocslib.pdfparser import DocumentAnalysisParser

from .mocks import MockAzureCredential

TEST_DATA_DIR = pathlib.Path(__file__).parent / "test-data"


@pytest.fixture
def sample_image():
    """Fixture for a sample ImageOnPage object used across multiple tests."""
    return ImageOnPage(
        bytes=b"fake",
        bbox=(0, 0, 100, 100),
        page_num=1,
        figure_id="fig_1",
        placeholder='<figure id="fig_1"></figure>',
        filename="test.png",
    )


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

    cropped_image_bytes, bbox_pixels = DocumentAnalysisParser.crop_image_from_pdf_page(doc, page_number, bounding_box)

    # Verify the output is not empty
    assert cropped_image_bytes is not None
    assert len(cropped_image_bytes) > 0
    assert bbox_pixels is not None
    assert len(bbox_pixels) == 4
    assert bbox_pixels == (105.86, 204.27, 398.74, 475.36)  # Coordinates in pixels

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
async def test_process_figure_without_bounding_regions():
    figure = DocumentFigure(id="1", caption=None, bounding_regions=None)
    result = await DocumentAnalysisParser.figure_to_image(None, figure)

    assert isinstance(result, ImageOnPage)
    assert result.description is None
    assert result.title == ""
    assert result.figure_id == "1"
    assert result.page_num == 0
    assert result.bbox == (0, 0, 0, 0)
    assert result.filename == "figure1.png"


@pytest.mark.asyncio
async def test_process_figure_with_bounding_regions(monkeypatch, caplog):
    doc = MagicMock()
    figure = DocumentFigure(
        id="1",
        caption=DocumentCaption(content="Logo"),
        bounding_regions=[
            BoundingRegion(page_number=1, polygon=[1.4703, 2.8371, 5.5409, 2.8415, 5.5381, 6.6022, 1.4681, 6.5978]),
            BoundingRegion(page_number=2, polygon=[1.4703, 2.8371, 5.5409, 2.8415, 5.5381, 6.6022, 1.4681, 6.5978]),
        ],
    )

    def mock_crop_image_from_pdf_page(doc, page_number, bounding_box):
        assert page_number == 0
        assert bounding_box == (1.4703, 2.8371, 5.5381, 6.6022)
        return b"image_bytes", [10, 20, 30, 40]

    monkeypatch.setattr(DocumentAnalysisParser, "crop_image_from_pdf_page", mock_crop_image_from_pdf_page)

    with caplog.at_level(logging.WARNING):
        result = await DocumentAnalysisParser.figure_to_image(doc, figure)

        assert isinstance(result, ImageOnPage)
        assert result.description is None
        assert result.title == "Logo"
        assert result.bytes == b"image_bytes"
        assert result.page_num == 0
        assert result.figure_id == "1"
        assert result.bbox == [10, 20, 30, 40]
        assert result.filename == "figure1.png"
        assert "Figure 1 has more than one bounding region, using the first one" in caplog.text


@pytest.mark.asyncio
async def test_parse_simple(monkeypatch):
    mock_poller = MagicMock()
    captured_bodies: list[AnalyzeDocumentRequest] = []

    async def mock_begin_analyze_document(self, model_id, **kwargs):
        body = kwargs["body"]
        captured_bodies.append(body)
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
    )
    content = io.BytesIO(b"pdf content bytes")
    content.name = "test.pdf"
    pages = [page async for page in parser.parse(content)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Page content"
    assert len(captured_bodies) == 1
    assert isinstance(captured_bodies[0], AnalyzeDocumentRequest)
    assert captured_bodies[0].bytes_source == b"pdf content bytes"


@pytest.mark.asyncio
async def test_parse_with_filestorage(monkeypatch):
    mock_poller = MagicMock()
    captured_bodies: list[AnalyzeDocumentRequest] = []

    async def mock_begin_analyze_document(self, model_id, **kwargs):
        captured_bodies.append(kwargs["body"])
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
    )
    stream = io.BytesIO(b"pdf content bytes")
    file_storage = FileStorage(stream=stream, filename="upload.pdf")
    file_storage.name = "upload.pdf"
    pages = [page async for page in parser.parse(file_storage)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Page content"
    assert len(captured_bodies) == 1
    assert isinstance(captured_bodies[0], AnalyzeDocumentRequest)
    assert captured_bodies[0].bytes_source == b"pdf content bytes"


@pytest.mark.asyncio
async def test_parse_with_non_seekable_stream(monkeypatch):
    mock_poller = MagicMock()
    captured_bodies: list[AnalyzeDocumentRequest] = []

    async def mock_begin_analyze_document(self, model_id, **kwargs):
        captured_bodies.append(kwargs["body"])
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

    class NonSeekableStream:
        def __init__(self, data: bytes, name: str):
            self._data = data
            self._name = name
            self._consumed = False

        @property
        def name(self) -> str:  # type: ignore[override]
            return self._name

        def read(self) -> bytes:
            return self._data

    parser = DocumentAnalysisParser(
        endpoint="https://example.com",
        credential=MockAzureCredential(),
    )

    stream = NonSeekableStream(b"pdf content bytes", "nonseekable.pdf")
    pages = [page async for page in parser.parse(stream)]

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Page content"
    assert len(captured_bodies) == 1
    assert isinstance(captured_bodies[0], AnalyzeDocumentRequest)
    assert captured_bodies[0].bytes_source == b"pdf content bytes"


@pytest.mark.asyncio
async def test_parse_doc_with_tables(monkeypatch):
    mock_poller = MagicMock()
    captured_bodies: list[AnalyzeDocumentRequest] = []

    async def mock_begin_analyze_document(self, model_id, **kwargs):
        captured_bodies.append(kwargs["body"])
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
        endpoint="https://example.com",
        credential=MockAzureCredential(),
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
    assert len(captured_bodies) == 1
    assert isinstance(captured_bodies[0], AnalyzeDocumentRequest)


@pytest.mark.asyncio
async def test_parse_doc_with_figures(monkeypatch):
    mock_poller = MagicMock()
    captured_kwargs: list[dict] = []

    async def mock_begin_analyze_document(self, model_id, **kwargs):
        captured_kwargs.append(kwargs)
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

    parser = DocumentAnalysisParser(
        endpoint="https://example.com", credential=MockAzureCredential(), process_figures=True
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
        == '# Simple Figure\n\nThis text is before the figure and NOT part of it.\n\n\n<figure id="1.1"></figure>\n\n\nThis is text after the figure that\'s not part of it.'
    )
    assert pages[0].images[0].placeholder == '<figure id="1.1"></figure>'
    assert len(captured_kwargs) == 1
    body = captured_kwargs[0]["body"]
    assert isinstance(body, AnalyzeDocumentRequest)
    assert captured_kwargs[0]["output"] == ["figures"]
    assert captured_kwargs[0]["features"] == ["ocrHighResolution"]


@pytest.mark.asyncio
async def test_parse_unsupportedformat(monkeypatch, caplog):
    mock_poller = MagicMock()
    captured_kwargs: list[dict] = []

    async def mock_begin_analyze_document(self, model_id, **kwargs):
        captured_kwargs.append(kwargs)

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
        endpoint="https://example.com", credential=MockAzureCredential(), process_figures=True
    )
    content = io.BytesIO(b"pdf content bytes")
    content.name = "test.docx"
    with caplog.at_level(logging.ERROR):
        pages = [page async for page in parser.parse(content)]
        assert "does not support media description." in caplog.text

    assert len(pages) == 1
    assert pages[0].page_num == 0
    assert pages[0].offset == 0
    assert pages[0].text == "Page content"
    assert len(captured_kwargs) == 2
    assert captured_kwargs[0]["features"] == ["ocrHighResolution"]
    assert isinstance(captured_kwargs[0]["body"], AnalyzeDocumentRequest)
    assert captured_kwargs[1].get("features") is None
    assert isinstance(captured_kwargs[1]["body"], AnalyzeDocumentRequest)


@pytest.mark.asyncio
async def test_figure_processor_openai_requires_client():
    figure_processor = FigureProcessor(strategy=MediaDescriptionStrategy.OPENAI)

    with pytest.raises(ValueError, match="requires both a client and a model name"):
        await figure_processor.describe(b"bytes")


@pytest.mark.asyncio
async def test_figure_processor_openai_describe(monkeypatch):
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.OPENAI,
        openai_client=Mock(),
        openai_model="gpt-4o",
        openai_deployment="gpt-4o",
    )

    describer = AsyncMock()
    describer.describe_image.return_value = "Pie chart"

    async def fake_get_media_describer(self):
        return describer

    monkeypatch.setattr(FigureProcessor, "get_media_describer", fake_get_media_describer)

    result = await figure_processor.describe(b"bytes")

    assert result == "Pie chart"
    describer.describe_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_figure_processor_content_understanding_initializes_once(monkeypatch):
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
        credential=MockAzureCredential(),
        content_understanding_endpoint="https://example.com",
    )

    class FakeDescriber:
        def __init__(self, endpoint, credential):
            self.endpoint = endpoint
            self.credential = credential
            self.create_analyzer = AsyncMock()
            self.describe_image = AsyncMock(return_value="A diagram")

    monkeypatch.setattr("prepdocslib.figureprocessor.ContentUnderstandingDescriber", FakeDescriber)

    result_first = await figure_processor.describe(b"image")
    assert result_first == "A diagram"
    describer_instance = figure_processor.media_describer  # type: ignore[attr-defined]
    assert isinstance(describer_instance, FakeDescriber)
    describer_instance.create_analyzer.assert_awaited_once()

    result_second = await figure_processor.describe(b"image")
    assert result_second == "A diagram"
    assert describer_instance.create_analyzer.await_count == 1


@pytest.mark.asyncio
async def test_figure_processor_none_strategy_returns_none():
    figure_processor = FigureProcessor(strategy=MediaDescriptionStrategy.NONE)

    describer = await figure_processor.get_media_describer()
    assert describer is None

    result = await figure_processor.describe(b"bytes")
    assert result is None


@pytest.mark.asyncio
async def test_figure_processor_content_understanding_missing_endpoint():
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
        credential=MockAzureCredential(),
    )

    with pytest.raises(ValueError, match="Content Understanding strategy requires an endpoint"):
        await figure_processor.get_media_describer()


@pytest.mark.asyncio
async def test_figure_processor_content_understanding_missing_credential():
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
        content_understanding_endpoint="https://example.com",
    )

    with pytest.raises(ValueError, match="Content Understanding strategy requires a credential"):
        await figure_processor.get_media_describer()


@pytest.mark.asyncio
async def test_figure_processor_content_understanding_key_credential():
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
        credential=AzureKeyCredential("fake_key"),
        content_understanding_endpoint="https://example.com",
    )

    with pytest.raises(ValueError, match="Content Understanding does not support key credentials"):
        await figure_processor.get_media_describer()


@pytest.mark.asyncio
async def test_figure_processor_openai_returns_describer(monkeypatch):
    mock_client = Mock()
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.OPENAI,
        openai_client=mock_client,
        openai_model="gpt-4o",
        openai_deployment="gpt-4o-deployment",
    )

    describer = await figure_processor.get_media_describer()
    assert describer is not None
    assert figure_processor.media_describer is describer

    # Second call should return the same instance
    describer2 = await figure_processor.get_media_describer()
    assert describer2 is describer


@pytest.mark.asyncio
async def test_figure_processor_unknown_strategy(caplog):
    # Create a processor with an invalid strategy by patching the enum
    figure_processor = FigureProcessor(strategy=MediaDescriptionStrategy.NONE)
    # Override the strategy to an unknown value
    figure_processor.strategy = "unknown_strategy"  # type: ignore[assignment]

    with caplog.at_level(logging.WARNING):
        describer = await figure_processor.get_media_describer()

    assert describer is None
    assert "Unknown media description strategy" in caplog.text


@pytest.mark.asyncio
async def test_figure_processor_mark_content_understanding_ready():
    figure_processor = FigureProcessor(strategy=MediaDescriptionStrategy.NONE)

    assert not figure_processor.content_understanding_ready
    figure_processor.mark_content_understanding_ready()
    assert figure_processor.content_understanding_ready


@pytest.mark.asyncio
async def test_build_figure_markup_without_description(sample_image):
    sample_image.title = "Sample Figure"

    result = build_figure_markup(sample_image, description=None)
    assert result == "<figure><figcaption>fig_1 Sample Figure</figcaption></figure>"


@pytest.mark.asyncio
async def test_process_page_image_without_blob_manager(sample_image):
    with pytest.raises(ValueError, match="BlobManager must be provided"):
        await process_page_image(
            image=sample_image,
            document_filename="test.pdf",
            blob_manager=None,
            image_embeddings_client=None,
        )


@pytest.mark.asyncio
async def test_process_page_image_without_figure_processor(sample_image):

    blob_manager = AsyncMock()
    blob_manager.upload_document_image = AsyncMock(return_value="https://example.com/image.png")

    result = await process_page_image(
        image=sample_image,
        document_filename="test.pdf",
        blob_manager=blob_manager,
        image_embeddings_client=None,
        figure_processor=None,
    )

    assert result.description is None
    assert result.url == "https://example.com/image.png"
    blob_manager.upload_document_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_page_image_sets_description(sample_image):

    blob_manager = AsyncMock()
    blob_manager.upload_document_image = AsyncMock(return_value="https://example.com/image.png")

    figure_processor = AsyncMock()
    figure_processor.describe = AsyncMock(return_value="A bar chart")

    result = await process_page_image(
        image=sample_image,
        document_filename="test.pdf",
        blob_manager=blob_manager,
        image_embeddings_client=None,
        figure_processor=figure_processor,
    )

    assert result.description == "A bar chart"
    figure_processor.describe.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_page_image_skips_upload_if_url_exists(sample_image):

    sample_image.url = "https://existing.com/image.png"

    blob_manager = AsyncMock()
    blob_manager.upload_document_image = AsyncMock()

    result = await process_page_image(
        image=sample_image,
        document_filename="test.pdf",
        blob_manager=blob_manager,
        image_embeddings_client=None,
    )

    assert result.url == "https://existing.com/image.png"
    blob_manager.upload_document_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_page_image_with_embeddings(sample_image):

    blob_manager = AsyncMock()
    blob_manager.upload_document_image = AsyncMock(return_value="https://example.com/image.png")

    image_embeddings = AsyncMock()
    image_embeddings.create_embedding_for_image = AsyncMock(return_value=[0.1, 0.2, 0.3])

    result = await process_page_image(
        image=sample_image,
        document_filename="test.pdf",
        blob_manager=blob_manager,
        image_embeddings_client=image_embeddings,
    )

    assert result.embedding == [0.1, 0.2, 0.3]
    image_embeddings.create_embedding_for_image.assert_awaited_once()


def test_image_on_page_from_skill_payload_without_bytes():
    """Test ImageOnPage.from_skill_payload when bytes_base64 is not provided."""
    payload = {
        "filename": "test.png",
        "figure_id": "fig_1",
        "page_num": "1",
        "bbox": [0, 0, 100, 100],
        "document_file_name": "test.pdf",
    }

    image, doc_filename = ImageOnPage.from_skill_payload(payload)

    assert image.bytes == b""
    assert image.filename == "test.png"
    assert image.figure_id == "fig_1"
    assert image.page_num == 1
    assert image.bbox == (0, 0, 100, 100)
    assert doc_filename == "test.pdf"


def test_image_on_page_from_skill_payload_invalid_page_num():
    """Test ImageOnPage.from_skill_payload with invalid page_num."""
    payload = {
        "filename": "test.png",
        "figure_id": "fig_1",
        "page_num": "invalid",
        "bbox": [0, 0, 100, 100],
    }

    image, _ = ImageOnPage.from_skill_payload(payload)

    assert image.page_num == 0


def test_image_on_page_from_skill_payload_invalid_bbox():
    """Test ImageOnPage.from_skill_payload with invalid bbox."""
    payload = {
        "filename": "test.png",
        "figure_id": "fig_1",
        "page_num": 1,
        "bbox": [0, 0, 100],  # Only 3 elements
    }

    image, _ = ImageOnPage.from_skill_payload(payload)

    assert image.bbox == (0, 0, 0, 0)
