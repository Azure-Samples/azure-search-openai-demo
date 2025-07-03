import logging
from typing import Optional

from azure.core.credentials import AzureKeyCredential

from .blobmanager import BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .fileprocessor import FileProcessor
from .listfilestrategy import File, ListFileStrategy
from .mediadescriber import ContentUnderstandingDescriber
from .searchmanager import SearchManager, Section
from .strategy import DocumentAction, SearchInfo, Strategy

logger = logging.getLogger("scripts")


async def parse_file(
    file: File,
    file_processors: dict[str, FileProcessor],
    category: Optional[str] = None,
    blob_manager: Optional[BlobManager] = None,
    image_embeddings_client: Optional[ImageEmbeddings] = None,
    user_oid: Optional[str] = None,
) -> list[Section]:
    key = file.file_extension().lower()
    processor = file_processors.get(key)
    if processor is None:
        logger.info("Skipping '%s', no parser found.", file.filename())
        return []
    logger.info("Ingesting '%s'", file.filename())
    pages = [page async for page in processor.parser.parse(content=file.content)]
    for page in pages:
        for image in page.images:
            if not blob_manager or not image_embeddings_client:
                raise ValueError("BlobManager and ImageEmbeddingsClient must be provided to parse images in the file.")
            if image.url is None:
                image.url = await blob_manager.upload_document_image(
                    file.filename(), image.bytes, image.filename, image.page_num, user_oid=user_oid
                )
            if image_embeddings_client:
                image.embedding = await image_embeddings_client.create_embedding(image.bytes)
    logger.info("Splitting '%s' into sections", file.filename())
    sections = [
        Section(split_page, content=file, category=category) for split_page in processor.splitter.split_pages(pages)
    ]
    # For now, add the images back to each split page based off split_page.page_num
    for section in sections:
        section.split_page.images = [
            image for page in pages if page.page_num == section.split_page.page_num for image in page.images
        ]
    return sections


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        search_field_name_embedding: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
        use_content_understanding: bool = False,
        content_understanding_endpoint: Optional[str] = None,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.file_processors = file_processors
        self.document_action = document_action
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.search_field_name_embedding = search_field_name_embedding
        self.search_info = search_info
        self.use_acls = use_acls
        self.category = category
        self.use_content_understanding = use_content_understanding
        self.content_understanding_endpoint = content_understanding_endpoint

    def setup_search_manager(self):
        self.search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,
            self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.image_embeddings is not None,
        )

    async def setup(self):
        self.setup_search_manager()
        await self.search_manager.create_index()

        if self.use_content_understanding:
            if self.content_understanding_endpoint is None:
                raise ValueError("Content Understanding is enabled but no endpoint was provided")
            if isinstance(self.search_info.credential, AzureKeyCredential):
                raise ValueError(
                    "AzureKeyCredential is not supported for Content Understanding, use keyless auth instead"
                )
            cu_manager = ContentUnderstandingDescriber(self.content_understanding_endpoint, self.search_info.credential)
            await cu_manager.create_analyzer()

    async def run(self):
        self.setup_search_manager()
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    await self.blob_manager.upload_blob(file)
                    sections = await parse_file(
                        file, self.file_processors, self.category, self.blob_manager, self.image_embeddings
                    )
                    if sections:
                        await self.search_manager.update_content(sections, url=file.url)
                finally:
                    if file:
                        file.close()
        elif self.document_action == DocumentAction.Remove:
            paths = self.list_file_strategy.list_paths()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await self.search_manager.remove_content(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await self.search_manager.remove_content()


class UploadUserFileStrategy(FileStrategy):
    """
    Strategy for ingesting a file that has already been uploaded to a ADLS2 storage account
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_field_name_embedding: Optional[str] = None,
        blob_manager: Optional[BlobManager] = None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.blob_manager = blob_manager
        self.search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_int_vectorization=False,
            embeddings=self.embeddings,
            field_name_embedding=search_field_name_embedding,
            search_images=False,
        )
        self.search_field_name_embedding = search_field_name_embedding

    async def add_file(self, file: File, user_oid: str):
        sections = await parse_file(
            file, self.file_processors, None, self.blob_manager, self.image_embeddings, user_oid=user_oid
        )
        if sections:
            await self.search_manager.update_content(sections, url=file.url)

    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
