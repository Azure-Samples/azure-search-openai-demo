import openai
import os

from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from text import nonewlines
from typing import Any
from langchain.llms import AzureOpenAI
from langchain.chains import LLMChain

from core.messagebuilder import MessageBuilder
from langchain.prompts.prompt import PromptTemplate
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    system_chat_template = \
"You are an AI assistant that helps people find information." + \
"Use 'you' to refer to the individual asking the questions even if they ask with 'I'. " + \
"Answer the following question using only the data provided in the sources below. " + \
"For tabular information return it as an html table. Do not return markdown format. "  + \
"Simply complete the text withot coming up with a follow up example." + \
"Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. " + \
"If you cannot answer using the sources below, say you don't know. Below is an example.\n\n###"

    #shots/sample conversation
    question = """
'What is the deductible for the employee plan for a visit to Overlake in Bellevue?' 

Sources:
info1.txt: deductibles depend on whether you are in-network or out-of-network. In-network deductibles are $500 for employee and $1000 for family. Out-of-network deductibles are $1000 for employee and $2000 for family.
info2.pdf: Overlake is in-network for the employee plan.
info3.pdf: Overlake is the name of the area that includes a park and ride near Bellevue.
info4.pdf: In-network institutions include Overlake, Swedish and others in the region
"""
    answer = "In-network deductibles are $500 for employee and $1000 for family [info1.txt] and Overlake is in-network for the employee plan [info2.pdf][info4.pdf].\n###"

    def __init__(self, search_client: SearchClient, openai_deployment: str, chatgpt_model: str, openai_api_key: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.chatgpt_model = chatgpt_model
        openai.api_key = openai_api_key
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def run(self, q: str, overrides: dict[str, Any]) -> Any:
        has_text = "text"
        has_vector = None
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        # If retrieval mode includes vectors, compute an embedding for the query

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        query_text = q if has_text else None

        # Use semantic ranker if requested and if retrieval mode is text or hybrid (vectors + text)
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
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        message_builder = MessageBuilder(overrides.get("prompt_template") or self.system_chat_template, self.chatgpt_model)

        # add user question
        user_content = q + "\n" + f"Sources:\n {content}"
        message_builder.append_message('user', "Question:\n" + user_content+"\n\nAnswer:\n")

        # Add shots/samples. This helps model to mimic response and make sure they match rules laid out in system message.
        message_builder.append_message('assistant', "Answer:\n"+self.answer)
        message_builder.append_message('user', "Question:\n"+self.question)

        messages = message_builder.messages
        prompt = ChatPromptTemplate.from_messages(messages=messages)
        print(messages)
        llm = AzureOpenAI(deployment_name=self.openai_deployment, 
                          temperature=overrides.get("temperature") or 0.7, 
                          openai_api_base=openai.api_base, 
                          openai_api_key=openai.api_key,
                          openai_api_version=openai.api_version)

        
        chain = LLMChain(prompt=prompt, llm=llm)
        answer=chain.run({})
       
        return {"data_points": results, "answer": answer, "thoughts": f"Question:<br>{query_text}<br><br>Prompt:<br>" + prompt.format()}
