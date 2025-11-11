import os
from io import BytesIO

import pytest
from azure.search.documents.aio import SearchClient

from prepdocslib.blobmanager import BlobManager
from prepdocslib.figureprocessor import FigureProcessor, MediaDescriptionStrategy
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy, parse_file
from prepdocslib.listfilestrategy import (
    ADLSGen2ListFileStrategy,
    File,
    LocalListFileStrategy,
)
from prepdocslib.page import ImageOnPage, Page
from prepdocslib.strategy import SearchInfo
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SimpleTextSplitter

from .mocks import MockAzureCredential


@pytest.mark.asyncio
async def test_file_strategy_adls2(monkeypatch, mock_env, mock_data_lake_service_client):
    adlsgen2_list_strategy = ADLSGen2ListFileStrategy(
        data_lake_storage_account="a", data_lake_filesystem="a", data_lake_path="a", credential=MockAzureCredential()
    )
    blob_manager = BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        account=os.environ["AZURE_STORAGE_ACCOUNT"],
        resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    )

    # Set up mocks used by upload_blob
    async def mock_exists(*args, **kwargs):
        return True

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

    uploaded_to_blob = []

    async def mock_upload_blob(self, name, *args, **kwargs):
        uploaded_to_blob.append(name)

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

    search_info = SearchInfo(
        endpoint="https://testsearchclient.blob.core.windows.net",
        credential=MockAzureCredential(),
        index_name="test",
    )

    uploaded_to_search = []

    async def mock_upload_documents(self, documents):
        uploaded_to_search.extend(documents)

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    file_strategy = FileStrategy(
        list_file_strategy=adlsgen2_list_strategy,
        blob_manager=blob_manager,
        search_info=search_info,
        file_processors={".txt": FileProcessor(TextParser(), SimpleTextSplitter())},
        use_acls=True,
    )

    await file_strategy.run()

    assert len(uploaded_to_blob) == 0
    assert len(uploaded_to_search) == 3
    assert uploaded_to_search == [
        {
            "id": "file-a_txt-612E7478747B276F696473273A205B27412D555345522D4944275D2C202767726F757073273A205B27412D47524F55502D4944275D7D-page-0",
            "content": "texttext",
            "category": None,
            "groups": ["A-GROUP-ID"],
            "oids": ["A-USER-ID"],
            "sourcepage": "a.txt",
            "sourcefile": "a.txt",
            "storageUrl": "https://test.blob.core.windows.net/a.txt",
        },
        {
            "id": "file-b_txt-622E7478747B276F696473273A205B27422D555345522D4944275D2C202767726F757073273A205B27422D47524F55502D4944275D7D-page-0",
            "content": "texttext",
            "category": None,
            "groups": ["B-GROUP-ID"],
            "oids": ["B-USER-ID"],
            "sourcepage": "b.txt",
            "sourcefile": "b.txt",
            "storageUrl": "https://test.blob.core.windows.net/b.txt",
        },
        {
            "id": "file-c_txt-632E7478747B276F696473273A205B27432D555345522D4944275D2C202767726F757073273A205B27432D47524F55502D4944275D7D-page-0",
            "content": "texttext",
            "category": None,
            "groups": ["C-GROUP-ID"],
            "oids": ["C-USER-ID"],
            "sourcepage": "c.txt",
            "sourcefile": "c.txt",
            "storageUrl": "https://test.blob.core.windows.net/c.txt",
        },
    ]


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
