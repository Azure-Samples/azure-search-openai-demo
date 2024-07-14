from typing import Awaitable, Callable

from openai import AsyncOpenAI

from .base_client import BaseAPIClient


class LocalOpenAIClient(BaseAPIClient, AsyncOpenAI):

    AsyncAzureADTokenProvider = Callable[[], "str | Awaitable[str]"]

    def __init__(self, *args, **kwargs) -> None:
        BaseAPIClient.__init__(self)
        AsyncOpenAI.__init__(self, *args, **kwargs)

    async def chat_completion(
        self,
        *args,
        **kwargs,
    ):
        return await self.chat.completions.create(*args, **kwargs)

    def format_message(self, message: str):
        return message
