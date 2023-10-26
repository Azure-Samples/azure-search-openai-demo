from abc import ABC
from typing import Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient, SearchIndexerClient

USER_AGENT = "azure-search-chat-demo/1.0.0"


class SearchInfo:
    def __init__(
        self,
        endpoint: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        index_name: str,
        verbose: bool = False,
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.index_name = index_name
        self.verbose = verbose

    def create_search_client(self) -> SearchClient:
        return SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)

    def create_search_index_client(self) -> SearchIndexClient:
        return SearchIndexClient(endpoint=self.endpoint, credential=self.credential)

    def create_search_indexer_client(self) -> SearchIndexerClient:
        return SearchIndexerClient(endpoint=self.endpoint, credential=self.credential)


class Strategy(ABC):
    async def setup(self, search_info: SearchInfo):
        raise NotImplementedError

    async def run(self, search_info: SearchInfo):
        raise NotImplementedError
