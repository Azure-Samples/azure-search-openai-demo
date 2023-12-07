import unicodedata

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
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
            ChatCompletionSystemMessageParam(role="system", content=self.normalize_content(system_content))
        ]
        self.model = chatgpt_model

    def insert_message(self, role: str, content: str, index: int = 1):
        """
        Inserts a message into the conversation at the specified index,
        or at index 1 (after system message) if no index is specified.
        Args:
            role (str): The role of the message sender (either "user", "system", or "assistant").
            content (str): The content of the message.
            index (int): The index at which to insert the message.
        """
        message: ChatCompletionMessageParam
        if role == "user":
            message = ChatCompletionUserMessageParam(role="user", content=self.normalize_content(content))
        elif role == "system":
            message = ChatCompletionSystemMessageParam(role="system", content=self.normalize_content(content))
        elif role == "assistant":
            message = ChatCompletionAssistantMessageParam(role="assistant", content=self.normalize_content(content))
        else:
            raise ValueError(f"Invalid role: {role}")
        self.messages.insert(index, message)

    def count_tokens_for_message(self, message: dict[str, str]):
        return num_tokens_from_messages(message, self.model)

    def normalize_content(self, content: str):
        return unicodedata.normalize("NFC", content)
