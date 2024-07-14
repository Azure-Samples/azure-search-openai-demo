from typing import Awaitable, Callable

from openai import AsyncAzureOpenAI

from .base_client import BaseAPIClient


class AzureOpenAIClient(BaseAPIClient, AsyncAzureOpenAI):

    AsyncAzureADTokenProvider = Callable[[], "str | Awaitable[str]"]

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        BaseAPIClient.__init__(self)
        AsyncAzureOpenAI.__init__(self, *args, **kwargs)

    async def chat_completion(
        self,
        *args,
        **kwargs,
    ):
        return await self.chat.completions.create(*args, **kwargs)

    async def create_embedding(self, input: str, model: str = None, **kwargs):
        embedding = await self.embeddings.create(input=input, model=model, **kwargs)
        return embedding.data[0].embedding

    def format_message(self, message: str):
        return message
