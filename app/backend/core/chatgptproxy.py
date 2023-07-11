from core.IChatGptProxy import IChatGptProxy
from modelhelper import get_token_limit
import openai

class ChatGptProxy(IChatGptProxy):
    def __init__(self, openai_instance: openai, chatgpt_deployment: str, chatgpt_model: str, gpt_deployment: str):
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.gpt_deployment = gpt_deployment
        self._token_limit = get_token_limit(chatgpt_model)
        self._openai = openai_instance
    
    