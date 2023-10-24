import hashlib
import os
import tempfile
import time
from abc import ABC
from enum import Enum
from glob import glob
from typing import IO, Any, AsyncGenerator, Generator, List, Optional, Union

import openai
import tiktoken
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.filedatalake.aio import (
    DataLakeServiceClient,
)
from scripts.prepdocs.strategy import Strategy
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


class DocumentAction(Enum):
    Add = 0
    Delete = 1
    DeleteAll = 2


class OpenAIEmbeddings(ABC):
    SUPPORTED_BATCH_AOAI_MODEL = {"text-embedding-ada-002": {"token_limit": 8100, "max_batch_size": 16}}

    def create_embedding_arguments(self) -> dict[str, Any]:
        raise NotImplementedError

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.disable_batch:
            return await self.create_embedding_batch(texts)
        else:
            embeddings = [await self.create_embedding(text) for text in texts]
            return embeddings

    def before_retry_sleep(self):
        if self.verbose:
            print("Rate limited on the OpenAI embeddings API, sleeping before retrying...")

    @classmethod
    def calculate_token_length(self, text: str):
        encoding = tiktoken.encoding_for_model(self.open_ai_model_name)
        return len(encoding.encode(text))

    def split_text_into_batches(self, texts: List[str]) -> Generator[List[str]]:
        batch_info = OpenAIEmbeddings.SUPPORTED_BATCH_AOAI_MODEL.get(self.open_ai_model_name)
        if not batch_info:
            raise NotImplementedError(
                f"Model {self.open_ai_model_name} is not supported with batch embedding operations"
            )

        batch_token_limit = batch_info["token_limit"]
        batch_max_size = batch_info["max_batch_size"]
        batch = []
        batch_token_length = 0
        for text in texts:
            text_token_length = OpenAIEmbeddings.calculate_token_length(text)
            if batch_token_length + text_token_length >= batch_token_limit and len(batch) > 0:
                yield batch
                batch = []
                batch_token_length = 0

            batch.append(text)
            batch_token_length = batch_token_length + text_token_length
            if len(batch) == batch_max_size:
                yield batch
                batch = []
                batch_token_length = 0

        if len(batch) > 0:
            yield batch

    async def create_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        batches = list(self.split_text_into_batches(texts))
        for batch in batches:
            try:
                async for attempt in AsyncRetrying(
                    retry=retry_if_exception_type(openai.error.RateLimitError),
                    wait=wait_random_exponential(min=15, max=60),
                    stop=stop_after_attempt(15),
                ):
                    with attempt:
                        emb_response = await openai.Embedding.acreate(**self.create_embedding_arguments(), input=batch)
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
                    emb_response = await openai.Embedding.acreate(**self.create_embedding_arguments(), input=text)
                    return emb_response["data"][0]["embedding"]
        except RetryError:
            self.before_retry_sleep()


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
        self.credential = self.wrap_credential(credential)
        self.disable_batch = disable_batch
        self.cached_token = None

    def create_embedding_arguments(self) -> dict[str, Any]:
        return {
            "model": self.open_ai_model_name,
            "deployment_id": self.open_ai_deployment,
            "api_type": self.get_api_type(),
            "api_key": self.wrap_credential(),
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

    def create_embedding_arguments(self) -> dict[str, Any]:
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
        self.acls = acls

    def __enter__(self):
        return self

    def __exit__(self):
        self.content.close()


class ListFileStrategy(ABC):
    async def list(self) -> AsyncGenerator[File]:
        raise NotImplementedError


class LocalListFileStrategy(ListFileStrategy):
    def __init__(self, path_pattern: str):
        self.path_pattern = path_pattern

    async def list(self) -> AsyncGenerator[File]:
        async for f in self._list(self.path_pattern):
            yield f

    async def _list(self, path_pattern: str) -> AsyncGenerator[File]:
        for path in glob(path_pattern):
            if os.path.isdir(path):
                async for f in self._list(f"{path}/*"):
                    yield f

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

    async def list(self) -> AsyncGenerator[File]:
        service = DataLakeServiceClient(
            account_url=f"https://{self.data_lake_storage_account}.dfs.core.windows.net", credential=self.credential
        )
        filesystem = service.get_file_system_client(file_system=self.data_lake_file_system)
        paths = filesystem.get_paths(path=self.data_lake_path, recursive=True)
        async for path in paths:
            if path.is_directory:
                continue

            temp_file_path = os.path.join(tempfile.gettempdir(), os.path.basename(path.name))
            try:
                with open(temp_file_path, "wb") as temp_file:
                    file_client = filesystem.get_file_client(path)
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


class PdfParser(ABC):
    async def parse(self) -> List[Page]:
        raise NotImplementedError


class FileStrategy(Strategy):
    def __init__(
        list_file_strategy: ListFileStrategy,
        storage_account: str,
        storage_container: str,
        pdf_parser: PdfParser,
        embedding_service: OpenAIEmbeddingService,
        search_analyzer_name: str = None,
        storage_key: AzureKeyCredential = None,
        tenant_id: str = None,
        use_acls: bool = False,
        category: str = None,
        skip_blobs: bool = False,
        document_action: DocumentAction = DocumentAction.Add,
    ):
        raise NotImplementedError
