import inspect
from abc import ABC
from typing import List

from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai.types import CreateEmbeddingResponse
from openai.types.chat import ChatCompletion


class OpenAIClient(ABC):

    def __init__(self):
        self._client = None

    @property
    def allowed_chat_completion_params(self) -> List[str]:
        params = list(inspect.signature(self.client.chat.completions.create).parameters.keys())
        if "messages" in params:
            params.remove("messages")
        return params

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    async def chat_completion(self, *args, **kwargs) -> ChatCompletion:
        return await self.client.chat.completions.create(*args, **kwargs)

    async def create_embeddings(self, *args, **kwargs) -> CreateEmbeddingResponse:
        return await self.client.embeddings.create(*args, **kwargs)


class LocalOpenAIClient(OpenAIClient):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.client = AsyncOpenAI(*args, **kwargs)


class AzureOpenAIClient(OpenAIClient):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.client = AsyncAzureOpenAI(*args, **kwargs)
