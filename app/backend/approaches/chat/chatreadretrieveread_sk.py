from typing import Any, Sequence
import os

import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType

from approaches.approach import Approach
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit
from text import nonewlines

import semantic_kernel as sk
from semantic_kernel.core_skills.text_skill import TextSkill

from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion



class ChatReadRetrieveRead_SemanticKernel(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    system_message_chat_conversation = """Assistant helps the company employees with retrieving and summarizing data. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf]. {{$prompt_override}}
{{$history}}
Sources:{{$sources}}
User:{{$input}}
ChatBot:
"""
    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base.
Generate a search query based on the conversation and the new question.
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Do not include any special characters like '+'.
If the question is not in English, translate the question to English before generating the search query.
If you cannot generate a search query, return just the number 0.

#####
These are some examples:
Generate a search query for: does my plan cover cardio?
AI: Health plan cardio coverage

Generate a search query for: What is Medicare?
AI: medicare definition meaning
####

{{$history}}
Generate a search query for: {{$input}}
AI:
"""
    query_prompt_few_shots = [
        {'role' : USER, 'content' : '' },
        {'role' : ASSISTANT, 'content' : 'Show available health plans' },
        {'role' : USER, 'content' : '' },
        {'role' : ASSISTANT, 'content' : '' }
    ]

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, chatgpt_model: str, openai_api_key: str, openai_api_endpoint : str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)
        kernel = sk.Kernel()
        kernel.add_chat_service(
            "chat_completion",
            AzureChatCompletion(chatgpt_deployment, openai_api_endpoint, openai_api_key),
        )
        
        self.query = kernel.create_semantic_function(self.query_prompt_template, max_tokens=self.chatgpt_token_limit, temperature=0.7, top_p=0.5)
        self.answer = kernel.create_semantic_function(self.system_message_chat_conversation, max_tokens=self.chatgpt_token_limit, temperature=0.7, top_p=0.5)
        
        self.context = kernel.create_new_context()
        self.context["history"] = ""
        
        skills_directory = "./skills" 
        groundingSemanticFunctions = kernel.import_semantic_skill_from_directory(skills_directory, "GroundingSkill")
        

        self.entity_extraction = groundingSemanticFunctions["ExtractEntities"]
        self.reference_check = groundingSemanticFunctions["ReferenceCheckEntities"]
        self.entity_excision = groundingSemanticFunctions["ExciseEntities"]
        
        self.grounding_context = kernel.create_new_context()
        self.grounding_context["topic"] = "people, places, and companies"
        self.grounding_context["example_entities"] = "John, Jane, mother, brother, Paris, Rome, Disney, Amazon, coorporation"
        
        

    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False


        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        self.context["input"] = history[-1]["user"]

        query_text = self.query.invoke(context=self.context).result
        if query_text.strip() == "0":
            query_text = history[-1]["user"] 

        if overrides.get("semantic_ranker") and has_text:
            r = self.search_client.search(query_text,
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC,
                                          query_language="en-us",
                                          query_speller="lexicon",
                                          semantic_configuration_name="default",
                                          top=top)
        else:
            r = self.search_client.search(query_text,
                                          filter=filter,
                                          top=top)

        results = []
        refs = []
        for doc in r:
            if use_semantic_captions:
                doc_ref = doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']]))
            else:
                doc_ref = doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) 
            results.append(doc_ref)
            refs.append(doc[self.sourcepage_field])
        content = "\n".join(results)

        prompt_override = overrides.get("prompt_override")
        if prompt_override is None:
            prompt_override = ""
        self.context["prompt_override"] = prompt_override
        self.context["sources"] = content
        self.context["input"] = history[-1]["user"]
        chat_content = self.answer.invoke(context=self.context).result
        self.context["history"] += f"\nSources: {self.context['sources']}\nUser: {self.context['input']}"
        
   
        extraction_result = self.entity_extraction(chat_content, context=self.grounding_context)
        self.grounding_context["reference_context"] = self.context["history"]
        grounding_result = self.reference_check(extraction_result.result, context=self.grounding_context)
        self.grounding_context["ungrounded_entities"] = grounding_result.result
        chat_content = self.entity_excision(chat_content, context=self.grounding_context).result
 
        
        self.context["history"] += "\n{chat_content}"
        
        for ref in refs:
            chat_content += '[{ref}]'.format(ref=ref)
        
        msg_to_display = self.context["history"]
        
        
        return {"data_points": results, "answer": chat_content, "citations":refs, "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>" + msg_to_display.replace('\n', '<br>')}
