from core.modelhelper import num_tokens_from_messages

class MessageBuilder:

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

