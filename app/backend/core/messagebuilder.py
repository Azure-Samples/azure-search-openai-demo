from core.modelhelper import num_tokens_from_messages

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
        token_length(self) -> int: Returns the total token count in the conversation.
        to_messages(self) -> list: Returns the list of messages in the conversation.
    """
  def __init__(self, system_content: str, chatgpt_model: str):
    self.message = [{'role' : 'system', 'content': system_content}]
    self.model = chatgpt_model
    self.token_count = num_tokens_from_messages(self.message[-1], self.model)

  def append_message(self, role:str, content: str, index: int = 1):
    self.message.insert(index, {'role' : role, 'content': content})
    self.token_count += num_tokens_from_messages(self.message[index], self.model)
    return

  def token_length(self) -> int:
    return self.token_count

  def to_messages(self):
    return self.message

