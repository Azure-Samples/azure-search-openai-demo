import logging
import unicodedata
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any, Optional, Union

import tiktoken
from openai.types.chat import (
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
    ChatCompletionNamedToolChoiceParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai_messages_token_helper import model_helper
from openai_messages_token_helper.model_helper import (
    count_tokens_for_message,
    count_tokens_for_system_and_tools,
)
from transformers import AutoTokenizer  # type: ignore


def normalize_content(content: Union[str, Iterable[ChatCompletionContentPartParam]]):
    """
    Normalises the content of a message to NFC form to ensure the consistency between the messages format.
    Args:
        content (str | Iterable[ChatCompletionContentPartParam]): The content to normalise.
    Returns:
        (str | Iterable[ChatCompletionContentPartParam]): The normalised content.
    """
    if isinstance(content, str):
        return unicodedata.normalize("NFC", content)
    else:
        for part in content:
            if "image_url" not in part:
                part["text"] = unicodedata.normalize("NFC", part["text"])
        return content


def get_hf_encoding(model: Union[str, Any], *args) -> AutoTokenizer:
    """
    Get the Hugging Face tokenizer for a given model.
    Args:
        model (str): The name of the model to get the tokenizer for.
    Returns:
        AutoTokenizer: The tokenizer for the model.
    """
    try:
        return AutoTokenizer.from_pretrained(model)
    except ValueError:
        raise ValueError(f"Could not load the tokenizer for model {model}. Maybe this model is not supported?")


@contextmanager
def select_encoding(model_type: str):
    """
    Override the encoding for a given model and then restore it.
    Args:
        model (str): The name of the model to override the encoding for.
    """
    original_encoding_for_model = model_helper.encoding_for_model
    original_tiktoken_encoding = tiktoken.encoding_for_model

    def hugging_face_encoding(model, *args):
        return get_hf_encoding(model, *args)

    if model_type == "hf":
        model_helper.encoding_for_model = hugging_face_encoding
        tiktoken.encoding_for_model = hugging_face_encoding

    try:
        yield
    finally:
        model_helper.encoding_for_model = original_encoding_for_model
        tiktoken.encoding_for_model = original_tiktoken_encoding


def build_past_messages(
    model: str,
    model_type: str,
    system_message: str,
    max_tokens: int,
    *,
    tools: Optional[list[ChatCompletionToolParam]] = None,
    tool_choice: Optional[ChatCompletionNamedToolChoiceParam] = None,
    new_user_content: Union[str, list[ChatCompletionContentPartParam], None] = None,  # list is for GPT4v usage
    few_shots: Optional[list[ChatCompletionMessageParam]] = None,
    past_messages: list[ChatCompletionMessageParam] = [],  # *not* including system prompt
    fallback_to_default: bool = False,
) -> list[ChatCompletionMessageParam]:
    """
    Build a list of messages for a chat conversation, given the system prompt, new user message,
    and past messages. The function will truncate the history of past messages if necessary to
    stay within the token limit and return the truncated messages.
    Args:
        model (str): The model name to use for token calculation, like gpt-3.5-turbo.
        model_type (str): The type of the model to use for encoding [openai, hf].
        system_prompt (str): The initial system prompt message.
        tools (list[ChatCompletionToolParam]): A list of tools to include in the conversation.
        tool_choice (ChatCompletionNamedToolChoiceParam): The tool to use in the conversation.
        new_user_content (str | List[ChatCompletionContentPartParam]): Content of new user message to append.
        past_messages (list[ChatCompletionMessageParam]): The list of past messages in the conversation.
        few_shots (list[ChatCompletionMessageParam]): A few-shot list of messages to insert after the system prompt.
        max_tokens (int): The maximum number of tokens allowed for the conversation.
        fallback_to_default (bool): Whether to fallback to default model if the model is not found.
    Returns:
        list[ChatCompletionMessageParam]: Past messages truncated to fit within the token limit.
    """
    with select_encoding(model_type):
        total_token_count = count_tokens_for_system_and_tools(
            model,
            ChatCompletionSystemMessageParam(role="system", content=normalize_content(system_message)),
            tools,
            tool_choice,
            default_to_cl100k=fallback_to_default,
        )
        if few_shots:
            for shot in reversed(few_shots):
                if shot["role"] is None or shot["content"] is None:
                    raise ValueError("Few-shot messages must have both role and content")
                total_token_count += count_tokens_for_message(model, shot, default_to_cl100k=fallback_to_default)

        if new_user_content:
            total_token_count += count_tokens_for_message(
                model,
                ChatCompletionUserMessageParam(role="user", content=new_user_content),
                default_to_cl100k=fallback_to_default,
            )

        newest_to_oldest = list(reversed(past_messages))
        for index, message in enumerate(newest_to_oldest):
            potential_message_count = count_tokens_for_message(model, message, default_to_cl100k=fallback_to_default)

            if (total_token_count + potential_message_count) > max_tokens:
                logging.info("Reached max tokens of %d, history will be truncated", max_tokens)
                return newest_to_oldest[: index - 1]

            if message["role"] is None or message["content"] is None:
                raise ValueError("Few-shot messages must have both role and content")

            total_token_count += potential_message_count

        return past_messages
