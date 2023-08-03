from typing import Any, Sequence
import os
import openai
import tiktoken
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines
from azure.identity import DefaultAzureCredential

from langchain.llms import AzureOpenAI
from langchain.callbacks.manager import CallbackManager, Callbacks
from langchain.chains import LLMChain
from langchain.agents import Tool
from langchain.agents import AgentType
from langchain.memory import ConversationBufferMemory
from langchain import OpenAI
from langchain.utilities import SerpAPIWrapper
from langchain.agents import initialize_agent
from langchain.retrievers import AzureCognitiveSearchRetriever

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate

from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.prompts import PromptTemplate

from langchain.chains import ConversationalRetrievalChain
from langchain.chains import create_qa_with_sources_chain
from langchain.chains import RetrievalQA
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit

from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

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
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question. Do not generate questions and answers -- answer ONLY the last question by the user. 
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].cd.
"""
    template = """Combine the chat history and follow up question into 
    a standalone question. Chat History: {chat_history}
    Follow up question: {question}"""


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

        self.tools = [ ]
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
        azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential = True)

        # Used by the OpenAI SDK
        openai.api_type = "azure"
        openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
        openai.api_version = "2023-05-15"

        # Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
        openai.api_type = "azure_ad"
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
    

    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
       

        
        llm = AzureOpenAI(deployment_name=self.chatgpt_deployment, 
                          temperature=overrides.get("temperature") or 0.7, 
                          openai_api_base=openai.api_base, 
                          openai_api_key=openai.api_key, 
                          openai_api_version=openai.api_version)
        prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(
                    self.system_message_chat_conversation
                ),
                # The `variable_name` here is what must align with memory
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("The question: {question}")
            ],
            input_variables=["chat_history","question"]
        )
        # Notice that we need to align the `memory_key`
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        conversation_chain = LLMChain(
            llm=llm,
            prompt=prompt,
            verbose=True,
            memory=memory
        )
        
        
        #retriever = AzureCognitiveSearchRetriever(content_key="content", top_k=3)
        """qa_chain = create_qa_with_sources_chain(llm)
        doc_prompt = PromptTemplate(
            template="Content: {page_content}\nSource: {sourcepage}",
            input_variables=["page_content", "sourcepage"],
        )
        final_qa_chain = StuffDocumentsChain(
            llm_chain=qa_chain,
            document_variable_name="context",
            document_prompt=doc_prompt,
        )
        
        
        retrieval_chain = ConversationalRetrievalChain(
            question_generator=conversation_chain,
            retriever=retriever,
            memory=memory,
            combine_docs_chain=final_qa_chain
        )"""
        #retrieval_chain = RetrievalQA.from_chain_type(llm,retriever=retriever)

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        
        print(history)    
        result = conversation_chain({"question":history[0]["user"]})["text"]
        print(result)
        return {"data_points": "None" or [], "answer": result, "thoughts": "None" }# cb_handler.get_and_reset_log()}
    