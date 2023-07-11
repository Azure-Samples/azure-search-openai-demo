from core.IChatGptProxy import IChatGptProxy
from modelhelper import get_token_limit
import openai

class ChatGptProxy(IChatGptProxy):
    def __init__(self, openai_instance: openai, chatgpt_deployment: str, chatgpt_model: str, gpt_deployment: str):
        self.chatgpt_deployment = chatgpt_deployment
        self._chatgpt_model = chatgpt_model
        self.gpt_deployment = gpt_deployment
        self._token_limit = get_token_limit(chatgpt_model)
        self._openai = openai_instance
    
    def chat_completion(self, conversations: list(dict[str, str])) -> str:
      return ''


    def get_model_name(self) -> str:
        return self._chatgpt_model


    def get_token_limit(self) -> int:
        return self._token_limit  