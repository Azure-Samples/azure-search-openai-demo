import os  
import json  
import aiohttp  
from typing import List  
from botbuilder.core import ActivityHandler, TurnContext  
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes  
  
API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://app=backend-azurewebsites.net/chat")  
  
class ChatGptRequest:  
    def __init__(self, history: List, approach: str = "rrr", overrides=None):  
        self.history = history  
        self.approach = approach  
        self.overrides = overrides if overrides else OverRides()  
  
    def to_json(self):  
        return json.dumps(self, default=lambda o: o.__dict__)  
  
class OverRides:  
    def __init__(  
        self,  
        retrieval_mode: str = "hybrid",  
        semantic_ranker: bool = True,  
        semantic_captions: bool = True,  
        top: int = 5,  
        suggest_followup_questions: bool = True,  
    ):  
        self.retrieval_mode = retrieval_mode  
        self.semantic_ranker = semantic_ranker  
        self.semantic_captions = semantic_captions  
        self.top = top  
        self.suggest_followup_questions = suggest_followup_questions  
  
class ChatGptResponse:  
    def __init__(self, answer: str = "", **kwargs):  
        self.answer = answer  
  
    @classmethod  
    def from_json(cls, json_str: str):  
        if not json_str:  
            return cls(answer="No response from the API.")  
        try:  
            json_dict = json.loads(json_str)  
            return cls(**json_dict)  
        except json.JSONDecodeError:  
            return cls(answer="Invalid response format from the API.")  
  
async def chat_gpt_request(user_message: str) -> str:  
    history = [{"user": user_message}]  
    chat_gpt_request = ChatGptRequest(history=history)  
    payload = chat_gpt_request.to_json()  
  
    headers = {  
        "Content-Type": "application/json",  
    }  
  
    async with aiohttp.ClientSession() as session:  
        async with session.post(API_ENDPOINT, data=payload, headers=headers) as response:  
            response_text = await response.text()  
            api_response = ChatGptResponse.from_json(response_text)  
  
    return api_response.answer  
  
class MyBot(ActivityHandler):  
    async def on_message_activity(self, turn_context: TurnContext):  
        user_message = turn_context.activity.text  
        if user_message is not None:  
            response = await chat_gpt_request(user_message)  
            await turn_context.send_activity(response)  
  
    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):  
        for member_added in members_added:  
            if member_added.id != turn_context.activity.recipient.id:  
                await turn_context.send_activity("Hello and welcome!")  
