from modelhelper import num_tokens_from_messages

class MessageBuilder:

  def __init__(self, system_message:dict[str,str]):
    self.messsage = [{'role' : system_message['role'], 'content': system_message['content']}]
    self.token_count = num_tokens_from_messages(self.message[-1])

  def append_message(self, conversation: dict[str, str]):
    self.message.insert(1, {'role' : conversation['role'], 'content': conversation['content']})
    self.token_count += num_tokens_from_messages(self.message[1])
    return

  def token_length(self) -> int:
    return self.token_count

  def to_messages(self):
    return self.message

