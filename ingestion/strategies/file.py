"""
File-based ingestion strategies.

This module provides strategies for ingesting documents from local files
or Azure Data Lake Storage into Azure AI Search.
"""

import logging
from typing import Optional

from ..models import Chunk, File, Page, Section
from ..storage.blob import AdlsBlobManager, BaseBlobManager, BlobManager
from ..storage.file_lister import ListFileStrategy
from ..embeddings.text import OpenAIEmbeddings
from ..embeddings.image import ImageEmbeddings
from ..search.client import SearchInfo
from ..search.index_manager import SearchManager
from ..figures.processor import FigureProcessor, build_figure_markup, process_page_image
from .base import DocumentAction, Strategy

logger = logging.getLogger("ingestion")


def combine_text_with_figures(page: Page) -> None:
    """Replace figure placeholders in page text with full description markup."""
    for image in page.images:
        if image.description and image.placeholder in page.text:
            figure_markup = build_figure_markup(image, image.description)
            page.text = page.text.replace(image.placeholder, figure_markup)
            logger.info("Replaced placeholder for figure %s with description markup", image.figure_id)


def process_text(
    pages: list[Page],
    file: File,
    splitter,
    category: Optional[str] = None,
) -> list[Section]:
    """Process document text and figures into searchable sections."""
    # Combine text with figures on each page
    for page in pages:
        combine_text_with_figures(page)

    # Split combined text into chunks
    logger.info("Splitting '%s' into sections", file.filename())
    sections = [Section(chunk=chunk, content=file, category=category) for chunk in splitter.split_pages(pages)]

    # Add images back to each section based on page number
    for section in sections:
        section.chunk.images = [
            image for page in pages if page.page_num == section.chunk.page_num for image in page.images
        ]

    return sections


async def parse_file(
    file: File,
    file_processors: dict,
    category: Optional[str] = None,
    blob_manager: Optional[BaseBlobManager] = None,
    image_embeddings_client: Optional[ImageEmbeddings] = None,
    figure_processor: Optional[FigureProcessor] = None,
    user_oid: Optional[str] = None,
) -> list[Section]:
    """Parse a file and return a list of sections.

    Args:
        file: The file to parse
        file_processors: Dictionary mapping extensions to processors
        category: Optional category for the sections
        blob_manager: Optional blob manager for image uploads
        image_embeddings_client: Optional image embeddings client
        figure_processor: Optional figure processor for image descriptions
        user_oid: Optional user OID for access control

    Returns:
        List of Section objects
    """
    file_ext = file.file_extension().lower()
    processor = file_processors.get(file_ext)

    if processor is None:
        logger.warning("No processor found for file extension '%s', skipping file '%s'", file_ext, file.filename())
        return []

    logger.info("Processing file '%s' with extension '%s'", file.filename(), file_ext)

    # Parse the file into pages
    pages: list[Page] = []
    async for page in processor.parser.parse(file.content):
        # Process images on the page
        for image in page.images:
            if blob_manager is not None:
                await process_page_image(
                    image=image,
                    document_filename=file.filename(),
                    blob_manager=blob_manager,
                    image_embeddings_client=image_embeddings_client,
                    figure_processor=figure_processor,
                    user_oid=user_oid,
                )
        pages.append(page)

    # Process text and split into sections
    sections = process_text(pages, file, processor.splitter, category)

    return sections


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored
    either locally or in a data lake storage account.

    Attributes:
        list_file_strategy: Strategy for listing files to ingest
        blob_manager: Manager for blob storage operations
        file_processors: Dictionary mapping file extensions to processors
        document_action: Action to perform (Add, Remove, RemoveAll)
        embeddings: Text embeddings service
        image_embeddings: Image embeddings service
        search_info: Search service connection info
        use_acls: Whether to use access control lists
        category: Optional category for all ingested documents
        figure_processor: Optional processor for figures/images
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        file_processors: dict,
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        search_field_name_embedding: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
        figure_processor=None,
        enforce_access_control: bool = False,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False,
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
        self.figure_processor = figure_processor
        self.enforce_access_control = enforce_access_control
        self.use_web_source = use_web_source
        self.use_sharepoint_source = use_sharepoint_source

    def setup_search_manager(self):
        """Initialize the search manager."""
        self.search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,  # use_parent_index_projection disabled for file-based ingestion
            self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.image_embeddings is not None,
            enforce_access_control=self.enforce_access_control,
            use_web_source=self.use_web_source,
            use_sharepoint_source=self.use_sharepoint_source,
        )

    async def setup(self):
        """Set up the search index."""
        self.setup_search_manager()
        await self.search_manager.create_index()

    async def run(self):
        """Execute the file ingestion strategy."""
        self.setup_search_manager()
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    blob_url = await self.blob_manager.upload_blob(file)
                    sections = await parse_file(
                        file,
                        self.file_processors,
                        self.category,
                        self.blob_manager,
                        self.image_embeddings,
                        figure_processor=self.figure_processor,
                    )
                    if sections:
                        await self.search_manager.update_content(sections, url=blob_url)
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


class UploadUserFileStrategy:
    """
    Strategy for ingesting a file that has already been uploaded to an ADLS2 storage account.
    Used for user-uploaded files with access control.

    Attributes:
        file_processors: Dictionary mapping file extensions to processors
        embeddings: Text embeddings service
        image_embeddings: Image embeddings service
        search_info: Search service connection info
        blob_manager: ADLS blob manager for user files
        figure_processor: Optional processor for figures/images
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict,
        blob_manager: AdlsBlobManager,
        search_field_name_embedding: Optional[str] = None,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        enforce_access_control: bool = False,
        figure_processor=None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.blob_manager = blob_manager
        self.figure_processor = figure_processor
        self.search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_parent_index_projection=False,
            embeddings=self.embeddings,
            field_name_embedding=search_field_name_embedding,
            search_images=image_embeddings is not None,
            enforce_access_control=enforce_access_control,
        )
        self.search_field_name_embedding = search_field_name_embedding

    async def add_file(self, file: File, user_oid: str):
        """Add a user-uploaded file to the search index.

        Args:
            file: The file to add
            user_oid: The user's object ID for access control
        """
        sections = await parse_file(
            file,
            self.file_processors,
            None,
            self.blob_manager,
            self.image_embeddings,
            figure_processor=self.figure_processor,
            user_oid=user_oid,
        )
        if sections:
            await self.search_manager.update_content(sections, url=file.url)

    async def remove_file(self, filename: str, oid: str):
        """Remove a user-uploaded file from the search index.

        Args:
            filename: Name of the file to remove
            oid: The user's object ID
        """
        if filename is None or filename == "":
            logger.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
