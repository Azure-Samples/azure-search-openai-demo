import unicodedata

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
        append_message(self, role: str, content: str, index: int = 1): Appends a new message to the conversation.
    """

    def __init__(self, system_content: str, chatgpt_model: str):
        self.messages = [{"role": "system", "content": self.normalize_content(system_content)}]
        self.model = chatgpt_model
        self.token_length = num_tokens_from_messages(self.messages[-1], self.model)

    def append_message(self, role: str, content: str, index: int = 1):
        self.messages.insert(index, {"role": role, "content": self.normalize_content(content)})
        self.token_length += num_tokens_from_messages(self.messages[index], self.model)

    def normalize_content(self, content: str):
        return unicodedata.normalize("NFC", content)
