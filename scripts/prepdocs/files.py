import asyncio
import base64
import hashlib
import html
import io
import os
import re
import tempfile
import time
from abc import ABC
from enum import Enum
from glob import glob
from typing import IO, Any, AsyncGenerator, Generator, List, Optional, Union

import openai
import tiktoken
from azure.ai.formrecognizer import DocumentTable
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.indexes.models import (
    HnswParameters,
    PrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
)
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.filedatalake.aio import (
    DataLakeServiceClient,
)
from pypdf import PdfReader, PdfWriter
from scripts.prepdocs.strategy import SearchInfo, Strategy
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

USER_AGENT = "azure-search-chat-demo/1.0.0"


class DocumentAction(Enum):
    Add = 0
    Remove = 1
    RemoveAll = 2


class OpenAIEmbeddings(ABC):
    SUPPORTED_BATCH_AOAI_MODEL = {"text-embedding-ada-002": {"token_limit": 8100, "max_batch_size": 16}}

    async def create_embedding_arguments(self) -> dict[str, Any]:
        raise NotImplementedError

    def before_retry_sleep(self):
        if self.verbose:
            print("Rate limited on the OpenAI embeddings API, sleeping before retrying...")

    def calculate_token_length(self, text: str):
        encoding = tiktoken.encoding_for_model(self.open_ai_model_name)
        return len(encoding.encode(text))

    def split_text_into_batches(self, texts: List[str]) -> List[List[str]]:
        batch_info = OpenAIEmbeddings.SUPPORTED_BATCH_AOAI_MODEL.get(self.open_ai_model_name)
        if not batch_info:
            raise NotImplementedError(
                f"Model {self.open_ai_model_name} is not supported with batch embedding operations"
            )

        batch_token_limit = batch_info["token_limit"]
        batch_max_size = batch_info["max_batch_size"]
        batches = []
        batch = []
        batch_token_length = 0
        for text in texts:
            text_token_length = self.calculate_token_length(text)
            if batch_token_length + text_token_length >= batch_token_limit and len(batch) > 0:
                batches.append(batch)
                batch = []
                batch_token_length = 0

            batch.append(text)
            batch_token_length = batch_token_length + text_token_length
            if len(batch) == batch_max_size:
                batches.append(batch)
                batch = []
                batch_token_length = 0

        if len(batch) > 0:
            batches.append(batch)

        return batches

    async def create_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        batches = self.split_text_into_batches(texts)
        for batch in batches:
            try:
                async for attempt in AsyncRetrying(
                    retry=retry_if_exception_type(openai.error.RateLimitError),
                    wait=wait_random_exponential(min=15, max=60),
                    stop=stop_after_attempt(15),
                ):
                    with attempt:
                        emb_args = await self.create_embedding_arguments()
                        emb_response = await openai.Embedding.acreate(**emb_args, input=batch)
                        return [data["embedding"] for data in emb_response["data"]]
            except RetryError:
                self.before_retry_sleep()

    async def create_embedding_single(self, text: str) -> List[float]:
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(openai.error.RateLimitError),
                wait=wait_random_exponential(min=15, max=60),
                stop=stop_after_attempt(15),
            ):
                with attempt:
                    emb_args = await self.create_embedding_arguments()
                    emb_response = await openai.Embedding.acreate(**emb_args, input=text)
                    return emb_response["data"][0]["embedding"]
        except RetryError:
            self.before_retry_sleep()

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.disable_batch and self.open_ai_model_name in OpenAIEmbeddings.SUPPORTED_BATCH_AOAI_MODEL:
            return await self.create_embedding_batch(self, texts)

        return [await self.create_embedding_single(text) for text in texts]


class AzureOpenAIEmbeddingService(OpenAIEmbeddings):
    def __init__(
        self,
        open_ai_service: str,
        open_ai_deployment: str,
        open_ai_model_name: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        disable_batch: bool = False,
    ):
        self.open_ai_service = open_ai_service
        self.open_ai_deployment = open_ai_deployment
        self.open_ai_model_name = open_ai_model_name
        self.credential = credential
        self.disable_batch = disable_batch
        self.cached_token = None

    async def create_embedding_arguments(self) -> dict[str, Any]:
        return {
            "model": self.open_ai_model_name,
            "deployment_id": self.open_ai_deployment,
            "api_type": self.get_api_type(),
            "api_key": await self.wrap_credential(),
            "api_version": "2023-05-15",
        }

    def get_api_type(self) -> str:
        return "azure_ad" if self.credential is AsyncTokenCredential else "azure"

    async def wrap_credential(self) -> str:
        if self.credential is AzureKeyCredential:
            return self.credential.key

        if not self.cached_token or self.cached_token.expires_on <= time.time():
            self.cached_token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")

        return self.cached_token.token


class OpenAIEmbeddingService(OpenAIEmbeddings):
    def __init__(self, open_ai_model_name: str, credential: str, organization: str = None, disable_batch: bool = False):
        self.open_ai_model_name = open_ai_model_name
        self.credential = credential
        self.organization = organization
        self.disable_batch = disable_batch

    async def create_embedding_arguments(self) -> dict[str, Any]:
        return {
            "model": self.open_ai_model_name,
            "api_key": self.credential,
            "api_type": "openai",
            "organization": self.organization,
            "api_version": "2023-05-15",
        }


class File:
    def __init__(self, content: IO, acls: Optional[dict[str, list]] = None):
        self.content = content
        self.acls = acls or {}

    def __enter__(self):
        return self

    def __exit__(self):
        self.content.close()

    def filename(self):
        return os.path.basename(self.content.name)

    def filename_to_id(self):
        filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", self.content.name)
        filename_hash = base64.b16encode(self.content.name.encode("utf-8")).decode("ascii")
        return f"file-{filename_ascii}-{filename_hash}"


class ListFileStrategy(ABC):
    async def list(self) -> AsyncGenerator[File, None]:
        raise NotImplementedError

    async def list_paths(self) -> AsyncGenerator[str, None]:
        raise NotImplementedError


class LocalListFileStrategy(ListFileStrategy):
    def __init__(self, path_pattern: str):
        self.path_pattern = path_pattern

    async def list_paths(self) -> AsyncGenerator[str, None]:
        async for p in self._list_paths(self.path_pattern):
            yield p

    async def _list_paths(self, path_pattern: str) -> AsyncGenerator[str, None]:
        for path in glob(path_pattern):
            if os.path.isdir(path):
                async for p in self._list_paths(f"{path}/*"):
                    yield p

            yield path

    async def list(self) -> AsyncGenerator[File, None]:
        async for path in self.list_paths():
            if not self.check_md5(path):
                yield File(content=open(path, mode="rb"))

    def check_md5(self, path: str) -> bool:
        # if filename ends in .md5 skip
        if path.endswith(".md5"):
            return True

        # if there is a file called .md5 in this directory, see if its updated
        stored_hash = None
        with open(path, "rb") as file:
            existing_hash = hashlib.md5(file.read()).hexdigest()
        hash_path = f"{path}.md5"
        if os.path.exists(hash_path):
            with open(hash_path, encoding="utf-8") as md5_f:
                stored_hash = md5_f.read()

        if stored_hash and stored_hash.strip() == existing_hash.strip():
            if self.verbose:
                print(f"Skipping {path}, no changes detected.")
                return True

        # Write the hash
        with open(hash_path, "w", encoding="utf-8") as md5_f:
            md5_f.write(existing_hash)

        return False


class ADLSGen2ListFileStrategy(ListFileStrategy):
    def __init__(
        self,
        data_lake_storage_account: str,
        data_lake_filesystem: str,
        data_lake_path: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
    ):
        self.data_lake_storage_account = data_lake_storage_account
        self.data_lake_filesystem = data_lake_filesystem
        self.data_lake_path = data_lake_path
        self.credential = credential

    async def list_paths(self) -> AsyncGenerator[str, None]:
        async with DataLakeServiceClient(
            account_url=f"https://{self.data_lake_storage_account}.dfs.core.windows.net", credential=self.credential
        ) as service_client, service_client.get_file_system_client(
            file_system=self.data_lake_file_system
        ) as filesystem_client:
            paths = filesystem_client.get_paths(path=self.data_lake_path, recursive=True)
            async for path in paths:
                if path.is_directory:
                    continue

                yield path

    async def list(self) -> AsyncGenerator[File, None]:
        async with DataLakeServiceClient(
            account_url=f"https://{self.data_lake_storage_account}.dfs.core.windows.net", credential=self.credential
        ) as service_client, service_client.get_file_system_client(
            file_system=self.data_lake_file_system
        ) as filesystem_client:
            async for path in await self.list_paths():
                temp_file_path = os.path.join(tempfile.gettempdir(), os.path.basename(path.name))
                try:
                    with open(temp_file_path, "wb") as temp_file, filesystem_client.get_file_client(
                        path
                    ) as file_client:
                        downloader = await file_client.download_file()
                        await downloader.readinto(temp_file)

                    # Parse out user ids and group ids
                    acls = {"oids": [], "groups": []}
                    # https://learn.microsoft.com/python/api/azure-storage-file-datalake/azure.storage.filedatalake.datalakefileclient?view=azure-python#azure-storage-filedatalake-datalakefileclient-get-access-control
                    # Request ACLs as GUIDs
                    acl_list = file_client.get_access_control(upn=False)["acl"]
                    # https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control
                    # ACL Format: user::rwx,group::r-x,other::r--,user:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:r--
                    acl_list = acl_list.split(",")
                    for acl in acl_list:
                        acl_parts: list = acl.split(":")
                        if len(acl_parts) != 3:
                            continue
                        if len(acl_parts[1]) == 0:
                            continue
                        if acl_parts[0] == "user" and "r" in acl_parts[2]:
                            acls["oids"].append(acl_parts[1])
                        if acl_parts[0] == "group" and "r" in acl_parts[2]:
                            acls["groups"].append(acl_parts[1])

                    yield File(content=open(temp_file, "rb"), acls=acls)
                except Exception as e:
                    print(f"\tGot an error while reading {path.name} -> {e} --> skipping file")
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        print(f"\tGot an error while deleting {temp_file_path} -> {e}")


class Page:
    def __init__(self, page_num: int, offset: int, text: str):
        self.page_num = page_num
        self.offset = offset
        self.text = text


class SplitPage:
    def __init__(self, page_num: int, text: str):
        self.page_num = page_num
        self.text = text


class TextSplitter:
    def __init__(self):
        self.sentence_endings = [".", "!", "?"]
        self.word_breaks = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
        self.max_section_length = 1000
        self.sentence_search_limit = 100
        self.section_overlap = 100

    def split_pages(self, pages: List[Page]) -> Generator[SplitPage, None, None]:
        def find_page(offset):
            num_pages = len(pages)
            for i in range(num_pages - 1):
                if offset >= pages[i].offset and offset < pages[i + 1][1]:
                    return pages[i]
            return pages[num_pages - 1]

        all_text = "".join(page.text for page in pages)
        length = len(all_text)
        start = 0
        end = length
        while start + self.section_overlap < length:
            last_word = -1
            end = start + self.max_section_length

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while (
                    end < length
                    and (end - start - self.max_section_length) < self.sentence_search_limit
                    and all_text[end] not in self.sentence_endings
                ):
                    if all_text[end] in self.word_breaks:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in self.sentence_endings and last_word > 0:
                    end = last_word  # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while (
                start > 0
                and start > end - self.max_section_length - 2 * self.sentence_search_limit
                and all_text[start] not in self.sentence_endings
            ):
                if all_text[start] in self.word_breaks:
                    last_word = start
                start -= 1
            if all_text[start] not in self.sentence_endings and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield (section_text, find_page(start))

            last_table_start = section_text.rfind("<table")
            if last_table_start > 2 * self.sentence_search_limit and last_table_start > section_text.rfind("</table"):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
                # If last table starts inside section_overlap, keep overlapping
                if self.verbose:
                    print(
                        f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}"
                    )
                start = min(end - self.section_overlap, start + last_table_start)
            else:
                start = end - self.section_overlap

        if start + self.section_overlap < end:
            yield SplitPage(page_num=find_page(start), text=all_text[start:end])


class PdfParser(ABC):
    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        raise NotImplementedError


class LocalPdfParser(PdfParser):
    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        reader = PdfReader(content)
        pages = reader.pages
        offset = 0
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            yield Page(page_num=page_num, offset=offset, text=page_text)
            offset += len(page_text)


class DocumentAnalysisPdfParser(PdfParser):
    def __init__(
        self,
        endpoint: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        model_id="prebuilt-layout",
        verbose: bool = False,
    ):
        self.model_id = model_id
        self.endpoint = endpoint
        self.credential = credential
        self.verbose = verbose

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        if self.verbose:
            print(f"Extracting text from '{content.name}' using Azure Form Recognizer")

        async with DocumentAnalysisClient(
            endpoint=self.endpoint, credential=self.credential, headers={"x-ms-useragent": USER_AGENT}
        ) as form_recognizer_client:
            poller = await form_recognizer_client.begin_analyze_document(model_id=self.model_id, document=content)
            form_recognizer_results = await poller.result()

            offset = 0
            for page_num, page in enumerate(form_recognizer_results.pages):
                tables_on_page = [
                    table
                    for table in (form_recognizer_results.tables or [])
                    if table.bounding_regions and table.bounding_regions[0].page_number == page_num + 1
                ]

                # mark all positions of the table spans in the page
                page_offset = page.spans[0].offset
                page_length = page.spans[0].length
                table_chars = [-1] * page_length
                for table_id, table in enumerate(tables_on_page):
                    for span in table.spans:
                        # replace all table spans with "table_id" in table_chars array
                        for i in range(span.length):
                            idx = span.offset - page_offset + i
                            if idx >= 0 and idx < page_length:
                                table_chars[idx] = table_id

                # build page text by replacing characters in table spans with table html
                page_text = ""
                added_tables = set()
                for idx, table_id in enumerate(table_chars):
                    if table_id == -1:
                        page_text += form_recognizer_results.content[page_offset + idx]
                    elif table_id not in added_tables:
                        page_text += DocumentAnalysisPdfParser.table_to_html(tables_on_page[table_id])
                        added_tables.add(table_id)

                yield Page(page_num=page_num, offset=offset, text=page_text)
                offset += len(page_text)

    @classmethod
    def table_to_html(cls, table: DocumentTable):
        table_html = "<table>"
        rows = [
            sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index)
            for i in range(table.row_count)
        ]
        for row_cells in rows:
            table_html += "<tr>"
            for cell in row_cells:
                tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
                cell_spans = ""
                if cell.column_span > 1:
                    cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span > 1:
                    cell_spans += f" rowSpan={cell.row_span}"
                table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            table_html += "</tr>"
        table_html += "</table>"
        return table_html


class BlobManager:
    def __init__(
        self,
        endpoint: str,
        container: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        verbose: bool = False,
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.container = container
        self.verbose = verbose

    async def upload_blob(self, file: File):
        async with BlobServiceClient(
            account_url=self.endpoint, credential=self.credential
        ) as service_client, service_client.get_container_client(self.container) as container_client:
            if not await container_client.exists():
                await container_client.create_container()

                # if file is PDF split into pages and upload each page as a separate blob
                if os.path.splitext(file.content.name)[1].lower() == ".pdf":
                    reader = PdfReader(file.content)
                    pages = reader.pages
                    for i in range(len(pages)):
                        blob_name = BlobManager.blob_name_from_file_page(file.content.name, i)
                        if self.verbose:
                            print(f"\tUploading blob for page {i} -> {blob_name}")
                        f = io.BytesIO()
                        writer = PdfWriter()
                        writer.add_page(pages[i])
                        writer.write(f)
                        f.seek(0)
                        await container_client.upload_blob(blob_name, f, overwrite=True)
                else:
                    blob_name = BlobManager.blob_name_from_file_page(file.content.name)
                    await container_client.upload_blob(blob_name, file.content, overwrite=True)

    async def remove_blob(self, path: str = None):
        async with BlobServiceClient(
            account_url=self.endpoint, credential=self.credential
        ) as service_client, service_client.get_container_client(self.container) as container_client:
            if not await container_client.exists():
                return
            if path is None:
                blobs = container_client.list_blob_names()
            else:
                prefix = os.path.splitext(os.path.basename(path))[0]
                blobs = container_client.list_blob_names(name_starts_with=os.path.splitext(os.path.basename(prefix))[0])
            async for b in blobs:
                if path is not None and not re.match(f"{prefix}-\d+\.pdf", b):
                    continue
                if self.verbose:
                    print(f"\tRemoving blob {b}")
                await container_client.delete_blob(b)

    @classmethod
    def blob_name_from_file_page(cls, filename, page=0) -> str:
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return os.path.splitext(os.path.basename(filename))[0] + f"-{page}" + ".pdf"
        else:
            return os.path.basename(filename)


class Section:
    def __init__(self, split_page: SplitPage, content: File, category: Optional[str] = None):
        self.split_page = split_page
        self.content = content
        self.category = category


class SearchManager:
    def __init__(
        self,
        search_info: SearchInfo,
        search_analyzer_name: str = None,
        use_acls: bool = False,
        embeddings: Optional[OpenAIEmbeddings] = None,
    ):
        self.search_info = search_info
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.embeddings = embeddings

    async def create_index(self):
        if self.verbose:
            print(f"Ensuring search index {self.index_name} exists")

        async with self.search_info.create_search_index_client() as search_index_client:
            fields = [
                SimpleField(name="id", type="Edm.String", key=True),
                SearchableField(name="content", type="Edm.String", analyzer_name=self.search_analyzer_name),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    hidden=False,
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=1536,
                    vector_search_configuration="default",
                ),
                SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcepage", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcefile", type="Edm.String", filterable=True, facetable=True),
            ]
            if self.use_acls:
                fields.append(
                    SimpleField(
                        name="oids", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True
                    )
                )
                fields.append(
                    SimpleField(
                        name="groups", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True
                    )
                )

            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                semantic_settings=SemanticSettings(
                    configurations=[
                        SemanticConfiguration(
                            name="default",
                            prioritized_fields=PrioritizedFields(
                                title_field=None, prioritized_content_fields=[SemanticField(field_name="content")]
                            ),
                        )
                    ]
                ),
                vector_search=VectorSearch(
                    algorithm_configurations=[
                        VectorSearchAlgorithmConfiguration(
                            name="default", kind="hnsw", hnsw_parameters=HnswParameters(metric="cosine")
                        )
                    ]
                ),
            )
            if self.verbose:
                print(f"Creating or updating {self.index_name} search index")
            await search_index_client.create_or_update_index(index)

    async def update_content(self, sections: List[Section]):
        MAX_BATCH_SIZE = 1000
        section_batches = [sections[i : i + MAX_BATCH_SIZE] for i in range(0, len(sections), MAX_BATCH_SIZE)]

        async with self.search_info.create_search_client() as search_client:
            for batch in section_batches:
                embeddings = None
                if self.embeddings:
                    embeddings = self.embeddings.create_embeddings(
                        texts=[section.split_page.text for section in sections]
                    )
                documents = [
                    {
                        "id": f"{section.content.filename_to_id()}-page-{i}",
                        "content": section.split_page.text,
                        "category": section.category,
                        "sourcepage": BlobManager.blob_name_from_file_page(
                            filename=section.content.name, page=section.split_page.page_num
                        ),
                        "sourcefile": section.content.filename(),
                        "embedding": embeddings[i] if embeddings else None,
                        **section.content.acls,
                    }
                    for i, section in enumerate(batch)
                ]

                await search_client.upload_documents(documents)

    async def remove_content(self, path: str = None):
        if self.verbose:
            print(f"Removing sections from '{path or '<all>'}' from search index '{self.index_name}'")
        async with self.search_info.create_search_client() as search_client:
            while True:
                filter = None if path is None else f"sourcefile eq '{os.path.basename(path)}'"
                r = await search_client.search("", filter=filter, top=1000, include_total_count=True)
                if await r.get_count() == 0:
                    break
                removed_docs = await search_client.delete_documents(documents=[{"id": d["id"]} for d in r])
                if self.verbose:
                    print(f"\tRemoved {len(removed_docs)} sections from index")
                # It can take a few seconds for search results to reflect changes, so wait a bit
                await asyncio.sleep(2)


class FileStrategy(Strategy):
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
        category: str = None,
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
            files = await self.list_file_strategy.list()
            async for file in files:
                await self.blob_manager.upload_blob(file)
                pages = await self.pdf_parser.parse(content=file.content)
                sections = [
                    Section(split_page, content=file, category=self.category)
                    for split_page in self.text_splitter.split_pages(pages)
                ]
                await search_manager.update_content(sections)
        elif self.document_action == DocumentAction.Remove:
            paths = await self.list_file_strategy.list_names()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await search_manager.remove_content(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await search_manager.remove_content()
