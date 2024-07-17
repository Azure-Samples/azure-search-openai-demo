from typing import Union

from api_wrappers.hugging_face import HuggingFaceClient
from api_wrappers.openai import AzureOpenAIClient, LocalOpenAIClient, OpenAIClient

LLMClient = Union[HuggingFaceClient, OpenAIClient]

__all__ = ["HuggingFaceClient", "LocalOpenAIClient", "AzureOpenAIClient", "LLMClient"]
