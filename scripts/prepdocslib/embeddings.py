import time
from abc import ABC
from typing import Any, List, Optional, Union

import openai
import tiktoken
from azure.core.credentials import AccessToken, AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


class EmbeddingBatch:
    """
    Represents a batch of text that is going to be embedded
    """

    def __init__(self, texts: List[str], token_length: int):
        self.texts = texts
        self.token_length = token_length


class OpenAIEmbeddings(ABC):
    """
    Contains common logic across both OpenAI and Azure OpenAI embedding services
    Can split source text into batches for more efficient embedding calls
    """

    SUPPORTED_BATCH_AOAI_MODEL = {"text-embedding-ada-002": {"token_limit": 8100, "max_batch_size": 16}}

    def __init__(self, open_ai_model_name: str, disable_batch: bool = False, verbose: bool = False):
        self.open_ai_model_name = open_ai_model_name
        self.disable_batch = disable_batch
        self.verbose = verbose

    async def create_embedding_arguments(self) -> dict[str, Any]:
        raise NotImplementedError

    def before_retry_sleep(self, retry_state):
        if self.verbose:
            print("Rate limited on the OpenAI embeddings API, sleeping before retrying...")

    def calculate_token_length(self, text: str):
        encoding = tiktoken.encoding_for_model(self.open_ai_model_name)
        return len(encoding.encode(text))

    def split_text_into_batches(self, texts: List[str]) -> List[EmbeddingBatch]:
        batch_info = OpenAIEmbeddings.SUPPORTED_BATCH_AOAI_MODEL.get(self.open_ai_model_name)
        if not batch_info:
            raise NotImplementedError(
                f"Model {self.open_ai_model_name} is not supported with batch embedding operations"
            )

        batch_token_limit = batch_info["token_limit"]
        batch_max_size = batch_info["max_batch_size"]
        batches: List[EmbeddingBatch] = []
        batch: List[str] = []
        batch_token_length = 0
        for text in texts:
            text_token_length = self.calculate_token_length(text)
            if batch_token_length + text_token_length >= batch_token_limit and len(batch) > 0:
                batches.append(EmbeddingBatch(batch, batch_token_length))
                batch = []
                batch_token_length = 0

            batch.append(text)
            batch_token_length = batch_token_length + text_token_length
            if len(batch) == batch_max_size:
                batches.append(EmbeddingBatch(batch, batch_token_length))
                batch = []
                batch_token_length = 0

        if len(batch) > 0:
            batches.append(EmbeddingBatch(batch, batch_token_length))

        return batches

    async def create_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        batches = self.split_text_into_batches(texts)
        embeddings = []
        for batch in batches:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(openai.error.RateLimitError),
                wait=wait_random_exponential(min=15, max=60),
                stop=stop_after_attempt(15),
                before_sleep=self.before_retry_sleep,
            ):
                with attempt:
                    emb_args = await self.create_embedding_arguments()
                    emb_response = await openai.Embedding.acreate(**emb_args, input=batch.texts)
                    embeddings.extend([data["embedding"] for data in emb_response["data"]])
                    if self.verbose:
                        print(f"Batch Completed. Batch size  {len(batch.texts)} Token count {batch.token_length}")

        return embeddings

    async def create_embedding_single(self, text: str) -> List[float]:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(openai.error.RateLimitError),
            wait=wait_random_exponential(min=15, max=60),
            stop=stop_after_attempt(15),
            before_sleep=self.before_retry_sleep,
        ):
            with attempt:
                emb_args = await self.create_embedding_arguments()
                emb_response = await openai.Embedding.acreate(**emb_args, input=text)

        return emb_response["data"][0]["embedding"]

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.disable_batch and self.open_ai_model_name in OpenAIEmbeddings.SUPPORTED_BATCH_AOAI_MODEL:
            return await self.create_embedding_batch(texts)

        return [await self.create_embedding_single(text) for text in texts]


class AzureOpenAIEmbeddingService(OpenAIEmbeddings):
    """
    Class for using Azure OpenAI embeddings
    To learn more please visit https://learn.microsoft.com/azure/ai-services/openai/concepts/understand-embeddings
    """

    def __init__(
        self,
        open_ai_service: str,
        open_ai_deployment: str,
        open_ai_model_name: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        disable_batch: bool = False,
        verbose: bool = False,
    ):
        super().__init__(open_ai_model_name, disable_batch, verbose)
        self.open_ai_service = open_ai_service
        self.open_ai_deployment = open_ai_deployment
        self.credential = credential
        self.cached_token: Optional[AccessToken] = None

    async def create_embedding_arguments(self) -> dict[str, Any]:
        return {
            "model": self.open_ai_model_name,
            "deployment_id": self.open_ai_deployment,
            "api_type": self.get_api_type(),
            "api_key": await self.wrap_credential(),
            "api_version": "2023-05-15",
            "api_base": f"https://{self.open_ai_service}.openai.azure.com",
        }

    def get_api_type(self) -> str:
        return "azure_ad" if isinstance(self.credential, AsyncTokenCredential) else "azure"

    async def wrap_credential(self) -> str:
        if isinstance(self.credential, AzureKeyCredential):
            return self.credential.key

        if isinstance(self.credential, AsyncTokenCredential):
            if not self.cached_token or self.cached_token.expires_on <= time.time():
                self.cached_token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")

            return self.cached_token.token

        raise Exception("Invalid credential type")


class OpenAIEmbeddingService(OpenAIEmbeddings):
    """
    Class for using OpenAI embeddings
    To learn more please visit https://platform.openai.com/docs/guides/embeddings
    """

    def __init__(
        self,
        open_ai_model_name: str,
        credential: str,
        organization: Optional[str] = None,
        disable_batch: bool = False,
        verbose: bool = False,
    ):
        super().__init__(open_ai_model_name, disable_batch, verbose)
        self.credential = credential
        self.organization = organization

    async def create_embedding_arguments(self) -> dict[str, Any]:
        return {
            "model": self.open_ai_model_name,
            "api_key": self.credential,
            "api_type": "openai",
            "organization": self.organization,
        }
