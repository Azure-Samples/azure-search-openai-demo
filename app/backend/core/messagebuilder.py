import unicodedata
from collections.abc import Mapping
from typing import List, Union

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from .modelhelper import num_tokens_from_messages


class MessageBuilder:
    """
    A class for building and managing messages in a chat conversation.
    Attributes:
        message (list): A list of dictionaries representing chat messages.
        model (str): The name of the ChatGPT model.
        token_count (int): The total number of tokens in the conversation.
    Methods:
        __init__(self, system_content: str, chatgpt_model: str): Initializes the MessageBuilder instance.
        insert_message(self, role: str, content: str, index: int = 1): Inserts a new message to the conversation.
    """

    def __init__(self, system_content: str, chatgpt_model: str):
        self.messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=unicodedata.normalize("NFC", system_content))
        ]
        self.model = chatgpt_model

    def insert_message(self, role: str, content: Union[str, List[ChatCompletionContentPartParam]], index: int = 1):
        """
        Inserts a message into the conversation at the specified index,
        or at index 1 (after system message) if no index is specified.
        Args:
            role (str): The role of the message sender (either "user", "system", or "assistant").
            content (str | List[ChatCompletionContentPartParam]): The content of the message.
            index (int): The index at which to insert the message.
        """
        message: ChatCompletionMessageParam
        if role == "user":
            message = ChatCompletionUserMessageParam(role="user", content=self.normalize_content(content))
        elif role == "system" and isinstance(content, str):
            message = ChatCompletionSystemMessageParam(role="system", content=unicodedata.normalize("NFC", content))
        elif role == "assistant" and isinstance(content, str):
            message = ChatCompletionAssistantMessageParam(
                role="assistant", content=unicodedata.normalize("NFC", content)
            )
        else:
            raise ValueError(f"Invalid role: {role}")
        self.messages.insert(index, message)

    def count_tokens_for_message(self, message: Mapping[str, object]):
        return num_tokens_from_messages(message, self.model)

    def normalize_content(self, content: Union[str, List[ChatCompletionContentPartParam]]):
        if isinstance(content, str):
            return unicodedata.normalize("NFC", content)
        elif isinstance(content, list):
            for part in content:
                if "image_url" not in part:
                    part["text"] = unicodedata.normalize("NFC", part["text"])
            return content
