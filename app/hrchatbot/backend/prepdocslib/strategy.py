from abc import ABC
from enum import Enum
from typing import Optional, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient, SearchIndexerClient

USER_AGENT = "azure-search-chat-demo/1.0.0"


class SearchInfo:
    """
    Class representing a connection to a search service
    To learn more, please visit https://learn.microsoft.com/azure/search/search-what-is-azure-search
    """

    def __init__(
        self,
        endpoint: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        index_name: str,
        use_agentic_retrieval: Optional[bool] = False,
        agent_name: Optional[str] = None,
        agent_max_output_tokens: Optional[int] = None,
        azure_openai_searchagent_model: Optional[str] = None,
        azure_openai_searchagent_deployment: Optional[str] = None,
        azure_openai_endpoint: Optional[str] = None,
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.index_name = index_name
        self.agent_name = agent_name
        self.agent_max_output_tokens = agent_max_output_tokens
        self.use_agentic_retrieval = use_agentic_retrieval
        self.azure_openai_searchagent_model = azure_openai_searchagent_model
        self.azure_openai_searchagent_deployment = azure_openai_searchagent_deployment
        self.azure_openai_endpoint = azure_openai_endpoint

    def create_search_client(self) -> SearchClient:
        return SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)

    def create_search_index_client(self) -> SearchIndexClient:
        return SearchIndexClient(endpoint=self.endpoint, credential=self.credential)

    def create_search_indexer_client(self) -> SearchIndexerClient:
        return SearchIndexerClient(endpoint=self.endpoint, credential=self.credential)


class DocumentAction(Enum):
    Add = 0
    Remove = 1
    RemoveAll = 2


class Strategy(ABC):
    """
    Abstract strategy for ingesting documents into a search service. It has a single setup step to perform any required initialization, and then a run step that actually ingests documents into the search service.
    """

    async def setup(self):
        raise NotImplementedError

    async def run(self):
        raise NotImplementedError
