from typing import Any, Dict, Iterable, List, Optional, Union

from huggingface_hub import (
    AsyncInferenceClient,
    ChatCompletionOutput,
    ChatCompletionStreamOutput,
)

from .base_client import BaseAPIClient


class HuggingFaceClient(BaseAPIClient):

    def __init__(
        self,
        model: Optional[str] = None,
        token: str = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ):
        self.client = AsyncInferenceClient(token=token, model=model, timeout=timeout, headers=headers, cookies=cookies)

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
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
        tools: Optional[List[str]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> Union[ChatCompletionOutput, Iterable[ChatCompletionStreamOutput]]:
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

    async def create_embedding(self, input: str, model: str):
        embedding = await self.client.feature_extraction(text=input, model=model)
        return embedding

    def format_message(self, message: str):
        formatted_messages = []
        if message:
            # Handle the initial 'system' message by embedding it within the first 'user' message
            first_message = message[0]
            if first_message["role"] == "system":
                system_content = first_message["content"]
                message = message[1:]  # Remove the 'system' message from the list
            else:
                system_content = ""

            # Add the system content to the first user message if it exists
            if system_content and message and message[0]["role"] == "user":
                message[0]["content"] = system_content + "\n\n" + message[0]["content"]

            # Process the messages to ensure proper alternation of roles
            last_role = None
            for message in message:
                if last_role == message["role"]:
                    raise ValueError("Messages must alternate roles between user and assistant.")
                formatted_messages.append(message)
                last_role = message["role"]

            # Ensure the first message is from the user
            if formatted_messages[0]["role"] != "user":
                raise ValueError("The first message must be from the user.")

        return formatted_messages
