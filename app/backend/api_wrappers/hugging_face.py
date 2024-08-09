import inspect
from typing import AsyncIterable, Dict, Iterable, List, Optional, Union

from huggingface_hub import AsyncInferenceClient  # type: ignore
from huggingface_hub.inference._generated.types import (  # type: ignore
    ChatCompletionOutput,
    ChatCompletionStreamOutput,
)
from openai.types import CreateEmbeddingResponse
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)


class HuggingFaceClient:

    def __init__(
        self,
        model: Optional[str] = None,
        token: Union[str, bool, None] = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ):
        self.client = AsyncInferenceClient(model=model, token=token, timeout=timeout, headers=headers, cookies=cookies)

    @property
    def allowed_chat_completion_params(self) -> List[str]:
        params = list(inspect.signature(self.client.chat_completion).parameters.keys())
        if "messages" in params:
            params.remove("messages")
        return params

    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: Optional[str] = None,
        stream: bool = False,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[Dict[int, float]] = None,
        logprobs: Optional[int] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        seed: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[str, List[str]]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionToolParam]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> Union[ChatCompletionOutput, AsyncIterable[ChatCompletionStreamOutput]]:
        return await self.client.chat_completion(
            messages=messages,
            model=model,
            stream=stream,
            frequency_penalty=frequency_penalty,
            logit_bias=logit_bias,
            logprobs=logprobs,
            max_tokens=max_tokens,
            n=n,
            presence_penalty=presence_penalty,
            seed=seed,
            stop=stop,
            temperature=temperature,
            tool_choice=tool_choice,
            tool_prompt=tool_prompt,
            tools=tools,
            top_logprobs=top_logprobs,
            top_p=top_p,
        )

    async def create_embeddings(self, *args, **kwargs) -> CreateEmbeddingResponse:
        raise NotImplementedError

    def _extract_content_as_string(
        self,
        content: Union[str, Iterable[Union[ChatCompletionContentPartTextParam, ChatCompletionContentPartImageParam]]],
    ) -> str:
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            if "text" in content and content["type"] == "text":
                return content["text"]
            elif "image_url" in content and content["type"] == "image_url":
                return content["image_url"]["url"]

        return ""
