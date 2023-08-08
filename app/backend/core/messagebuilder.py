from .modelhelper import num_tokens_from_messages
from langchain.schema import AIMessage, HumanMessage, SystemMessage

class LangChainMessageBuilder:
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
        self.messages = [SystemMessage(content=system_content)]
        self.model = chatgpt_model


    """def append_message(self, role: str, content: str, index: int = 1):
        self.messages.insert(index, {'role': role, 'content': content})
        self.token_length += num_tokens_from_messages(
            self.messages[index], self.model)"""
            
    def append_message(self, role: str, content: str, index: int = 1):
        if role == "user":
            self.messages.insert(index, HumanMessage(content = content))
        elif role == "assistant":
            self.messages.insert(index, AIMessage(content = content))
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
        self.messages = [{'role': 'system', 'content': system_content}]
        self.model = chatgpt_model
        self.token_length = num_tokens_from_messages(
            self.messages[-1], self.model)

    def append_message(self, role: str, content: str, index: int = 1):
        self.messages.insert(index, {'role': role, 'content': content})
        self.token_length += num_tokens_from_messages(
            self.messages[index], self.model)
