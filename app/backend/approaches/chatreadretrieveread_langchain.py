from typing import Any, Sequence

import openai
import tiktoken
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines

from langchain.llms.openai import AzureOpenAI
from langchain.callbacks.manager import CallbackManager, Callbacks
from langchain.chains import LLMChain
from langchain.agents import Tool, ZeroShotAgent, AgentExecutor
from langchainadapters import HtmlCallbackHandler

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate

from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit

class ChatReadRetrieveReadApproach_LC(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    llm = AzureOpenAI

    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """
    system_message_chat_conversation = """You are an AI assistant that helps people find information. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
{injected_prompt}
"""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about employee healthcare plans and the employee handbook.
Generate a search query based on the conversation and the new question. 
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Do not include any special characters like '+'.
If the question is not in English, translate the question to English before generating the search query.
If you cannot generate a search query, return just the number 0.
"""
    query_prompt_few_shots = [
        {'role' : USER, 'content' : 'What are my health plans?' },
        {'role' : ASSISTANT, 'content' : 'Show available health plans' },
        {'role' : USER, 'content' : 'does my plan cover cardio?' },
        {'role' : ASSISTANT, 'content' : 'Health plan cardio coverage' }
    ]

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, chatgpt_model: str, embedding_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)

    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
        has_text = "text"
        has_vector = None
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
        query_vector = None

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        
        llm = AzureOpenAI(deployment_name=self.chatgpt_deployment, temperature=overrides.get("temperature") or 0.3, openai_api_key=openai.api_key)
        conversation = ConversationChain(
                llm=llm, verbose=True, memory=ConversationBufferMemory()
            )
        
        template = self.query_prompt_template
        '''PROMPT = PromptTemplate(input_variables=["history", "input"], template=template)
        conversation = ConversationChain(
            prompt=PROMPT,
            llm=llm,
            verbose=True,
            memory=ConversationBufferMemory(ai_prefix="AI Assistant"),
        )'''
        
            
        result = "Not implemented"
        return {"data_points": "None" or [], "answer": result, "thoughts": "None" }# cb_handler.get_and_reset_log()}
    
