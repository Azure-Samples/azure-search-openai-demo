from abc import ABC
from typing import Awaitable, Callable, List, Optional, Union
from urllib.parse import urljoin

import aiohttp
import tiktoken
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from openai import AsyncAzureOpenAI, AsyncOpenAI, RateLimitError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)
from typing_extensions import TypedDict


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

    async def create_client(self) -> AsyncOpenAI:
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
        client = await self.create_client()
        for batch in batches:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(RateLimitError),
                wait=wait_random_exponential(min=15, max=60),
                stop=stop_after_attempt(15),
                before_sleep=self.before_retry_sleep,
            ):
                with attempt:
                    emb_response = await client.embeddings.create(model=self.open_ai_model_name, input=batch.texts)
                    embeddings.extend([data.embedding for data in emb_response.data])
                    if self.verbose:
                        print(f"Batch Completed. Batch size  {len(batch.texts)} Token count {batch.token_length}")

        return embeddings

    async def create_embedding_single(self, text: str) -> List[float]:
        client = await self.create_client()
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(RateLimitError),
            wait=wait_random_exponential(min=15, max=60),
            stop=stop_after_attempt(15),
            before_sleep=self.before_retry_sleep,
        ):
            with attempt:
                emb_response = await client.embeddings.create(model=self.open_ai_model_name, input=text)

        return emb_response.data[0].embedding

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

    async def create_client(self) -> AsyncOpenAI:
        class AuthArgs(TypedDict, total=False):
            api_key: str
            azure_ad_token_provider: Callable[[], Union[str, Awaitable[str]]]

        auth_args = AuthArgs()
        if isinstance(self.credential, AzureKeyCredential):
            auth_args["api_key"] = self.credential.key
        elif isinstance(self.credential, AsyncTokenCredential):
            auth_args["azure_ad_token_provider"] = get_bearer_token_provider(
                self.credential, "https://cognitiveservices.azure.com/.default"
            )
        else:
            raise TypeError("Invalid credential type")

        return AsyncAzureOpenAI(
            azure_endpoint=f"https://{self.open_ai_service}.openai.azure.com",
            azure_deployment=self.open_ai_deployment,
            api_version="2023-05-15",
            **auth_args,
        )


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

    async def create_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self.credential, organization=self.organization)


class ImageEmbeddings:
    """
    Class for using image embeddings from Azure AI Vision
    To learn more, please visit https://learn.microsoft.com/azure/ai-services/computer-vision/how-to/image-retrieval#call-the-vectorize-image-api
    """

    def __init__(self, endpoint: str, token_provider: Callable[[], Awaitable[str]], verbose: bool = False):
        self.token_provider = token_provider
        self.endpoint = endpoint
        self.verbose = verbose

    async def create_embeddings(self, blob_urls: List[str]) -> List[List[float]]:
        endpoint = urljoin(self.endpoint, "computervision/retrieval:vectorizeImage")
        headers = {"Content-Type": "application/json"}
        params = {"api-version": "2023-02-01-preview", "modelVersion": "latest"}
        headers["Authorization"] = "Bearer " + await self.token_provider()

        embeddings: List[List[float]] = []
        async with aiohttp.ClientSession(headers=headers) as session:
            for blob_url in blob_urls:
                async for attempt in AsyncRetrying(
                    retry=retry_if_exception_type(Exception),
                    wait=wait_random_exponential(min=15, max=60),
                    stop=stop_after_attempt(15),
                    before_sleep=self.before_retry_sleep,
                ):
                    with attempt:
                        body = {"url": blob_url}
                        async with session.post(url=endpoint, params=params, json=body) as resp:
                            resp_json = await resp.json()
                            embeddings.append(resp_json["vector"])

        return embeddings

    def before_retry_sleep(self, retry_state):
        if self.verbose:
            print("Rate limited on the Vision embeddings API, sleeping before retrying...")
