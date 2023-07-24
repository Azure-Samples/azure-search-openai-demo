import os  
import json  
import aiohttp  
from typing import List  
from botbuilder.core import ActivityHandler, TurnContext  
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes  
from langchain.memory import ConversationBufferWindowMemory  
from langchain.agents import ConversationalChatAgent, AgentExecutor, Tool  
from langchain.llms import OpenAI  
from langchain.chat_models import ChatOpenAI  
from langchain.schema import BaseOutputParser, OutputParserException  
from langchain.chains import LLMChain  
from langchain.prompts import PromptTemplate  
  
API_ENDPOINT = os.environ.get("API_ENDPOINT", "")  #backend api endpoint "app-backend.azurewebsites.net/chat"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # OAI API KEY
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "")  
OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2023-05-15")  
  
class ChatGptRequest:  
    def __init__(self, history: List, approach: str = "rrr", overrides=None):  
        self.history = history  
        self.approach = approach  
        self.overrides = overrides if overrides else {}  
  
    def to_json(self):  
        return json.dumps(self, default=lambda o: o.__dict__)  
  
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
            return response_text  
  
llm = OpenAI(api_key=OPENAI_API_KEY, verbose=False)  
tools = [  
    Tool(  
        name="@chat",  
        func=chat_gpt_request,  
        description="useful when the questions include the term: @chat.\n",  
        return_direct=True,  
    ),  
]  
agent = ConversationalChatAgent.from_llm_and_tools(llm=llm, tools=tools)  
memory = ConversationBufferWindowMemory(memory_key="chat_history", return_messages=True, k=10)  
agent_chain = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True, memory=memory)  
  
class MyBot(ActivityHandler):  
    async def on_message_activity(self, turn_context: TurnContext):  
        user_message = turn_context.activity.text  
        if user_message is not None:  
            if "@chat" in user_message:  
                response = await chat_gpt_request(user_message)  
            else:  
                response = await agent_chain.run(user_message)  
            await turn_context.send_activity(response)  
  
    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):  
        for member_added in members_added:  
            if member_added.id != turn_context.activity.recipient.id:  
                await turn_context.send_activity("Hello and welcome!")  
