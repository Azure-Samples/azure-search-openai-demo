from typing import List, Optional

from .blobmanager import BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .fileprocessor import FileProcessor
from .listfilestrategy import ListFileStrategy
from .searchmanager import SearchManager, Section
from .strategy import DocumentAction, SearchInfo, Strategy


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        file_processors: dict[str, FileProcessor],
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.file_processors = file_processors
        self.document_action = document_action
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.category = category

    async def setup(self, search_info: SearchInfo):
        search_manager = SearchManager(
            search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,
            self.embeddings,
            search_images=self.image_embeddings is not None,
        )
        await search_manager.create_index()

    async def run(self, search_info: SearchInfo):
        search_manager = SearchManager(search_info, self.search_analyzer_name, self.use_acls, False, self.embeddings)
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    key = file.file_extension()
                    processor = self.file_processors.get(key)
                    if processor is None:
                        # skip file if no parser is found
                        if search_info.verbose:
                            print(f"Skipping '{file.filename()}'.")
                        continue
                    if search_info.verbose:
                        print(f"Parsing '{file.filename()}'")
                    pages = [page async for page in processor.parser.parse(content=file.content)]
                    if search_info.verbose:
                        print(f"Splitting '{file.filename()}' into sections")
                    sections = [
                        Section(split_page, content=file, category=self.category)
                        for split_page in processor.splitter.split_pages(pages)
                    ]

                    blob_sas_uris = await self.blob_manager.upload_blob(file)
                    blob_image_embeddings: Optional[List[List[float]]] = None
                    if self.image_embeddings and blob_sas_uris:
                        blob_image_embeddings = await self.image_embeddings.create_embeddings(blob_sas_uris)
                    await search_manager.update_content(sections, blob_image_embeddings)
                finally:
                    if file:
                        file.close()
        elif self.document_action == DocumentAction.Remove:
            paths = self.list_file_strategy.list_paths()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await search_manager.remove_content(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await search_manager.remove_content()
