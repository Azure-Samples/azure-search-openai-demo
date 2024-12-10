import logging
from typing import List, Optional

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
    image_embeddings: Optional[ImageEmbeddings] = None,
) -> List[Section]:
    key = file.file_extension().lower()
    processor = file_processors.get(key)
    if processor is None:
        logger.info("Skipping '%s', no parser found.", file.filename())
        return []
    logger.info("Ingesting '%s'", file.filename())
    pages = [page async for page in processor.parser.parse(content=file.content)]
    logger.info("Splitting '%s' into sections", file.filename())
    if image_embeddings:
        logger.warning("Each page will be split into smaller chunks of text, but images will be of the entire page.")
    sections = [
        Section(split_page, content=file, category=category) for split_page in processor.splitter.split_pages(pages)
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
        ignore_checksum: bool,
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
        use_content_understanding: bool = False,
        content_understanding_endpoint: Optional[str] = None,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.file_processors = file_processors
        self.document_action = document_action
        self.ignore_checksum = ignore_checksum
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.search_info = search_info
        self.use_acls = use_acls
        self.category = category
        self.use_content_understanding = use_content_understanding
        self.content_understanding_endpoint = content_understanding_endpoint

    async def setup(self):
        search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,
            self.embeddings,
            search_images=self.image_embeddings is not None,
        )
        await search_manager.create_index()

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
        search_manager = SearchManager(
            self.search_info, self.search_analyzer_name, self.use_acls, False, self.embeddings
        )
        doc_count = self.list_file_strategy.count_docs()
        logger.info("Processing %s files", doc_count)
        processed_count = 0
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    if not self.ignore_checksum and await search_manager.file_exists(file):
                        logger.info("'%s' has already been processed", file.filename())
                        continue
                    sections = await parse_file(file, self.file_processors, self.category, self.image_embeddings)
                    if sections:
                        blob_sas_uris = await self.blob_manager.upload_blob(file)
                        blob_image_embeddings: Optional[List[List[float]]] = None
                        if self.image_embeddings and blob_sas_uris:
                            blob_image_embeddings = await self.image_embeddings.create_embeddings(blob_sas_uris)
                        await search_manager.update_content(
                            sections=sections, file=file, image_embeddings=blob_image_embeddings
                        )
                finally:
                    if file:
                        file.close()
                processed_count += 1
                if processed_count % 10 == 0:
                    remaining = max(doc_count - processed_count, 1)
                    logger.info("%s processed, %s documents remaining", processed_count, remaining)

        elif self.document_action == DocumentAction.Remove:
            doc_count = self.list_file_strategy.count_docs()
            paths = self.list_file_strategy.list_paths()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await search_manager.remove_content(path)
                processed_count += 1
                if processed_count % 10 == 0:
                    remaining = max(doc_count - processed_count, 1)
                    logger.info("%s removed, %s documents remaining", processed_count, remaining)

        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await search_manager.remove_content()


class UploadUserFileStrategy:
    """
    Strategy for ingesting a file that has already been uploaded to a ADLS2 storage account
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.search_manager = SearchManager(self.search_info, None, True, False, self.embeddings)

    async def add_file(self, file: File):
        if self.image_embeddings:
            logging.warning("Image embeddings are not currently supported for the user upload feature")
        sections = await parse_file(file, self.file_processors)
        if sections:
            await self.search_manager.update_content(sections=sections, file=file)

    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
