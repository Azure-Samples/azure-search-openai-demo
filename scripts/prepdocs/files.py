from abc import ABC
from enum import Enum
from typing import Any, AsyncGenerator, List, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from scripts.prepdocs.strategy import Strategy


class DocumentAction(Enum):
    Add = 0
    Delete = 1
    DeleteAll = 2


class OpenAIEmbeddingService(ABC):
    def create_embedding_arguments(self) -> dict[str, Any]:
        raise NotImplementedError

    async def create_embeddings(self, texts: List[str]) -> List[float]:
        raise NotImplementedError


class AzureOpenAIEmbeddingService(OpenAIEmbeddingService):
    def __init__(
        open_ai_service: str,
        open_ai_deployment: str,
        open_ai_model_name: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        disable_batch: bool = False,
    ):
        pass


class NonAzureOpenAIEmbeddingService(OpenAIEmbeddingService):
    def __init__(open_ai_host: str, open_ai_model_name: str, credential: str, disable_batch: bool = False):
        pass


class EmbeddingInfo:
    def __init__(
        open_ai_host: str,
        open_ai_service: str,
        open_ai_deployment: str,
        open_ai_model_name: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        open_ai_org: str = None,
        disable_batch: bool = False,
    ):
        pass


class ListFileStrategy(ABC):
    async def list(self) -> AsyncGenerator[str]:
        raise NotImplementedError


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
