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

from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit
from langchain.prompts import (
    FewShotChatMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    FewShotPromptTemplate,
    PromptTemplate
)
from langchain.memory import ConversationBufferMemory
class ChatReadRetrieveReadApproach(Approach):
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
Only respond with a single sentence and nothing else. 
"""

    examples = [ {"input" : 'What are my health plans?',
                 "output" : 'Show available health plans'},
                 {"input": 'does my plan cover cardio?',
                 "output": 'Health plan cardio coverage'}]
    example_prompt = ChatPromptTemplate.from_messages(
        [('human', 'Generate search query for: {input}'), 
        ('ai', '{output}')]
        )
    example_prompt = FewShotChatMessagePromptTemplate(
        examples = examples,
        example_prompt = example_prompt,
        input_variables=['input', "output"]
    )
    
    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, chatgpt_model: str, openai_api_key : str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)
        openai.api_key = openai_api_key

        # Prepare OpenAI service using credentials stored in the `.env` file
        #api_key, org_id = sk.openai_settings_from_dot_env()

    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
        print(history)
        has_text = "text"
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None


        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        query_prompt = ChatPromptTemplate.from_messages([
               # self.example_prompt.format(),
                ("system", self.query_prompt_template) ,
                ("human", "Generate search query for: {user_query}")]
                )
    
        llm = AzureOpenAI(deployment_name=self.chatgpt_deployment, 
                          temperature=overrides.get("temperature") or 0.7, 
                          openai_api_base=openai.api_base, 
                          openai_api_key=openai.api_key,
                          openai_api_version=openai.api_version,
                          max_tokens=1024, 
                          n=1)

        read_chain = LLMChain(
            llm=llm,
            prompt=query_prompt,
            verbose=True,
            memory=memory
        )
        
        query_text = read_chain.run({"user_query": history[-1]["user"]})
        print(query_text)
        if query_text.strip() == "0":
            query_text = history[-1]["user"] # Use the last user input if we failed to generate a better query

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query

        # Use semantic L2 reranker if requested and if retrieval mode is text or hybrid (vectors + text)
        refs = []
        results = []
        if overrides.get("semantic_ranker") and has_text:
            r = self.search_client.search(query_text, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language="en-us", 
                                          query_speller="lexicon", 
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(query_text, 
                                          filter=filter, 
                                          top=top)
            
        
        for doc in r:
            if use_semantic_captions:
                doc_ref = doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']]))
            else:
                doc_ref = doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) 
            results.append(doc_ref)
            refs.append(doc[self.sourcepage_field])
        content = "\n".join(results)
        print(refs)
        
        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        system_message = self.system_message_chat_conversation
      
            
        message_prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_message_chat_conversation + "\n\nSources:\n" + content) ,
                ("human", "{user_query}")]
                )
        messages = self.get_messages_from_history(
            system_message + "\n\nSources:\n" + content,
            self.chatgpt_model,
            history,
            history[-1]["user"],
            max_tokens=self.chatgpt_token_limit)

        
        prompt = ChatPromptTemplate.from_messages(messages=messages)
        conversation_chain = LLMChain(
            llm=llm,
            prompt=message_prompt,
            verbose=True,
        )
        
        prompt_override =  overrides.get("prompt_override")
        if prompt_override is None: prompt_override = ""
        chat_content = conversation_chain.run({'user_query':history[-1]["user"], "injected_prompt":prompt_override})
        for ref in refs:
            chat_content += '[{ref}]'.format(ref=ref)
        print(chat_content)
        msg_to_display = '\n\n'.join([str(message) for message in messages])
        return {"data_points": results, "answer": chat_content, "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>" + msg_to_display.replace('\n', '<br>')}
    
    def get_messages_from_history(self, system_prompt: str, model_id: str, history: Sequence[dict[str, str]], user_conv: str, few_shots = [], max_tokens: int = 4096) -> []:
        message_builder = MessageBuilder(system_prompt, model_id)

        # Add examples to show the chat what responses we want. It will try to mimic any responses and make sure they match the rules laid out in the system message.
        for shot in few_shots:
            message_builder.append_message(shot.get('role'), shot.get('content'))

        user_content = user_conv
        append_index = len(few_shots) + 1

        message_builder.append_message(self.USER, user_content, index=append_index)

        for h in reversed(history[:-1]):
            if h.get("bot"):
                message_builder.append_message(self.ASSISTANT, h.get('bot'), index=append_index)
            message_builder.append_message(self.USER, h.get('user'), index=append_index)
            if message_builder.token_length > max_tokens:
                break
        
        messages = message_builder.messages
        return messages