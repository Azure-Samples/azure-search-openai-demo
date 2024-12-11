import logging
from typing import List, Optional
import sys
import os
import json

from .blobmanager import BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .fileprocessor import FileProcessor
from .listfilestrategy import File, ListFileStrategy
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
        blob_manager_search_index_files: BlobManager,
        blob_manager_interim_files: BlobManager,
        search_info: SearchInfo,
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
        self.blob_manager_search_index_files = blob_manager_search_index_files
        self.blob_manager_interim_files = blob_manager_interim_files
        self.file_processors = file_processors
        self.document_action = document_action
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.search_info = search_info
        self.use_acls = use_acls
        self.category = category

    async def setup(self):
        # mjh We are only saving files 
        logger.info("Not sending data to search, just creating files. Skipping index_update code.")
        # search_manager = SearchManager(
        #     self.search_info,
        #     self.search_analyzer_name,
        #     self.use_acls,
        #     False,
        #     self.embeddings,
        #     search_images=self.image_embeddings is not None,
        # )
        # await search_manager.create_index()

    async def cache_index_files(self, documents: List):
        cache_dir = "./data_interim/"
        for document in documents:
            output_dir = os.path.join(cache_dir, document["sourcefile"]) + "_index_files"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            file_name = document["sourcefile"] + "-" + document["id"]
            base_name = output_dir + "/" + file_name
            base_name += ".search_index_doc.json"
            # Here set fields
            if 'gao' in base_name.lower():
                document["dataSource"] = "gao"
            else:
                document["dataSource"] = "Unknown"
            if "embedding" in document:
                document["ContentVector"] = document["embedding"]
                del document["embedding"]
            with open(base_name, "w") as f:
                f.write(json.dumps(document, indent=4))
            file = File(content=open(base_name, mode="rb"))
            blob_sas_uris = await self.blob_manager_search_index_files.upload_blob(file)
            # Remove file to save space
            os.remove(base_name)
        os.rmdir(output_dir)

    async def run(self):
        search_manager = SearchManager(
            self.search_info, self.search_analyzer_name, self.use_acls, False, self.embeddings
        )
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()

            async for file in files:
                try:
                    sections = await parse_file(file, self.file_processors, self.category, self.image_embeddings)
                    if sections:
                        # mjh
                        #blob_sas_uris = await self.blob_manager.upload_blob(file)
                        blob_image_embeddings: Optional[List[List[float]]] = None
                        #if self.image_embeddings and blob_sas_uris:
                        if self.image_embeddings:
                            blob_image_embeddings = await self.image_embeddings.create_embeddings(blob_sas_uris) 
                        documents = await search_manager.update_content(sections, blob_image_embeddings, url=file.url)
                        # Save the index files, these will be indexed by a search instance later
                        if documents:
                            await self.cache_index_files(documents)

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
            await self.search_manager.update_content(sections, url=file.url)

    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
