from enum import Enum
from typing import Optional

from .blobmanager import BlobManager
from .embeddings import OpenAIEmbeddings
from .listfilestrategy import ListFileStrategy
from .pdfparser import PdfParser
from .searchmanager import SearchManager, Section
from .strategy import SearchInfo, Strategy
from .textsplitter import TextSplitter


class DocumentAction(Enum):
    Add = 0
    Remove = 1
    RemoveAll = 2


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        pdf_parser: PdfParser,
        text_splitter: TextSplitter,
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.pdf_parser = pdf_parser
        self.text_splitter = text_splitter
        self.document_action = document_action
        self.embeddings = embeddings
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.category = category

    async def setup(self, search_info: SearchInfo):
        search_manager = SearchManager(search_info, self.search_analyzer_name, self.use_acls, self.embeddings)
        await search_manager.create_index()

    async def run(self, search_info: SearchInfo):
        search_manager = SearchManager(search_info, self.search_analyzer_name, self.use_acls, self.embeddings)
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    pages = [page async for page in self.pdf_parser.parse(content=file.content)]
                    if search_info.verbose:
                        print(f"Splitting '{file.filename()}' into sections")
                    sections = [
                        Section(split_page, content=file, category=self.category)
                        for split_page in self.text_splitter.split_pages(pages)
                    ]
                    await search_manager.update_content(sections)
                    await self.blob_manager.upload_blob(file)
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
