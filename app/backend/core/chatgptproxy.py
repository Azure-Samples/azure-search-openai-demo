from core.ichatgptproxy import IChatGptProxy
from core.modelhelper import get_token_limit
import openai

class ChatGptProxy(IChatGptProxy):
    def __init__(self, openai_instance: openai, chatgpt_deployment: str, chatgpt_model: str, gpt_deployment: str):
        self.chatgpt_deployment = chatgpt_deployment
        self._chatgpt_model = chatgpt_model
        self.gpt_deployment = gpt_deployment
        self._token_limit = get_token_limit(chatgpt_model)
        self._openai = openai_instance
    
    def chat_completion(self, conversations: list(dict[str, str]), temperature:float = 0.7, max_tokens:int = 1024, n:int=1) -> str:
      chat_completion = self._openai.ChatCompletion.create(
            deployment_id=self.chatgpt_deployment,
            model=self._chatgpt_model,
            messages=conversations, 
            temperature=temperature, 
            max_tokens=max_tokens, 
            n=n)
        
      chat_content = chat_completion.choices[0].message.content
      return chat_content


    def get_model_name(self) -> str:
        return self._chatgpt_model


    def get_token_limit(self) -> int:
        return self._token_limit  