from typing import Any, Coroutine, List, Literal, Optional, Union, overload
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessageParam
from openai_messages_token_helper import build_messages, get_token_limit

from approaches.chatapproach import ChatApproach
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper

class RetrieveThenReadApproach(ChatApproach):
    """
    A chat approach that directly uses OpenAI's API without document retrieval.
    """

    def __init__(
        self,
        *,
        search_client,  # Keep parameter but won't use it
        auth_helper: AuthenticationHelper,
        openai_client: AsyncOpenAI,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],
        embedding_deployment: Optional[str],  # Keep parameter but won't use it
        embedding_model: str,
        embedding_dimensions: int,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        prompt_manager: PromptManager
    ):
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_token_limit = get_token_limit(chatgpt_model, default_to_minimum=self.ALLOW_NON_GPT_MODELS)
        self.prompt_manager = prompt_manager

    @overload
    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[False],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, ChatCompletion]]: ...

    @overload
    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[True],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, AsyncStream[ChatCompletionChunk]]]: ...

    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]]]:
        seed = overrides.get("seed", None)
        temperature = overrides.get("temperature", 0.7)  # Higher temperature for more creative chat
        
        # No document retrieval or search, just direct chat
        chat_coroutine = self.openai_client.chat.completions.create(
            model=self.chatgpt_deployment if self.chatgpt_deployment else self.chatgpt_model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            n=1,
            stream=should_stream,
            seed=seed,
        )

        # Minimal context since we're not doing retrieval
        extra_info = {
            "thoughts": []
        }

        return (extra_info, chat_coroutine)