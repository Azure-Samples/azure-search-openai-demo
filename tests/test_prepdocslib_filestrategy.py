import os
from io import BytesIO

import pytest

from prepdocslib.blobmanager import BlobManager
from prepdocslib.figureprocessor import FigureProcessor, MediaDescriptionStrategy
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy, parse_file
from prepdocslib.listfilestrategy import (
    File,
    LocalListFileStrategy,
)
from prepdocslib.page import ImageOnPage, Page
from prepdocslib.strategy import SearchInfo
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SimpleTextSplitter

from .mocks import MockAzureCredential


@pytest.mark.asyncio
async def test_parse_file_with_images(monkeypatch):
    """Test that parse_file processes images and logs appropriately."""

    # Create a mock file
    mock_file = File(content=BytesIO(b"test content"))
    mock_file.filename = lambda: "test.txt"

    # Create a mock processor
    mock_parser = type("MockParser", (), {})()

    async def mock_parse(content):
        # Create a page with an image
        image = ImageOnPage(
            bytes=b"fake_image",
            bbox=(0, 0, 100, 100),
            page_num=1,
            figure_id="fig_1",
            filename="test_image.png",
            placeholder='<figure id="fig_1"></figure>',
        )
        page = Page(page_num=1, text="Some text", offset=0)
        page.images = [image]
        yield page

    mock_parser.parse = mock_parse

    mock_splitter = type("MockSplitter", (), {})()
    mock_processor = type("MockProcessor", (), {"parser": mock_parser, "splitter": mock_splitter})()

    # Create mock blob manager
    mock_blob_manager = type("MockBlobManager", (), {})()

    async def mock_upload(*args, **kwargs):
        return "https://example.com/image.png"

    mock_blob_manager.upload_document_image = mock_upload

    # Create mock figure processor
    mock_figure_processor = type("MockFigureProcessor", (), {})()

    async def mock_describe(bytes):
        return "A test image"

    mock_figure_processor.describe = mock_describe

    # Mock process_text to return sections
    def mock_process_text(pages, file, splitter, category):
        return []

    monkeypatch.setattr("prepdocslib.filestrategy.process_text", mock_process_text)

    # Call parse_file
    sections = await parse_file(
        mock_file,
        {".txt": mock_processor},
        category=None,
        blob_manager=mock_blob_manager,
        image_embeddings_client=None,
        figure_processor=mock_figure_processor,
        user_oid=None,
    )

    assert sections == []


@pytest.mark.asyncio
async def test_file_strategy_setup_with_content_understanding(monkeypatch, mock_env):
    """Test that FileStrategy.setup() properly initializes content understanding."""

    # Create mock list strategy
    list_strategy = LocalListFileStrategy(path_pattern="*.txt")

    # Create blob manager
    blob_manager = BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        account=os.environ["AZURE_STORAGE_ACCOUNT"],
        resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    )

    # Create search info
    search_info = SearchInfo(
        endpoint="https://testsearchclient.blob.core.windows.net",
        credential=MockAzureCredential(),
        index_name="test",
    )

    # Create mock content understanding describer
    class MockContentUnderstandingDescriber:
        def __init__(self, endpoint, credential):
            self.endpoint = endpoint
            self.credential = credential
            self.create_analyzer_called = False

        async def create_analyzer(self):
            self.create_analyzer_called = True

    # Monkeypatch the ContentUnderstandingDescriber in multiple places
    monkeypatch.setattr("prepdocslib.figureprocessor.ContentUnderstandingDescriber", MockContentUnderstandingDescriber)
    monkeypatch.setattr("prepdocslib.filestrategy.ContentUnderstandingDescriber", MockContentUnderstandingDescriber)

    # Create figure processor with content understanding
    figure_processor = FigureProcessor(
        strategy=MediaDescriptionStrategy.CONTENTUNDERSTANDING,
        credential=MockAzureCredential(),
        content_understanding_endpoint="https://example.com",
    )

    # Mock create_index
    async def mock_create_index(self):
        pass

    monkeypatch.setattr("prepdocslib.searchmanager.SearchManager.create_index", mock_create_index)

    # Create file strategy
    file_strategy = FileStrategy(
        list_file_strategy=list_strategy,
        blob_manager=blob_manager,
        search_info=search_info,
        file_processors={".txt": FileProcessor(TextParser(), SimpleTextSplitter())},
        figure_processor=figure_processor,
    )

    # Call setup
    await file_strategy.setup()

    # Verify content understanding was initialized during setup
    assert figure_processor.media_describer is not None
    assert isinstance(figure_processor.media_describer, MockContentUnderstandingDescriber)
    # create_analyzer should be called during setup for content understanding
    assert figure_processor.media_describer.create_analyzer_called
    assert figure_processor.content_understanding_ready
