import os
import json
import logging
from typing import Any, AsyncGenerator, Optional, Union

import aiohttp
import openai
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType

from approaches.appresources import AppResources
from approaches.approach import Approach
from approaches.utils import Utils
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit
from text import nonewlines
from approaches.statetypes.statetype import StateType
from approaches.requestcontext import RequestContext

use_RAG = False

class StateTypeOpenAI(StateType):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    NO_RESPONSE = "0"

    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next about their healthcare plan and employee handbook.
Use double angle brackets to reference the questions, e.g. <<Are there exclusions for prescriptions?>>.
Try not to repeat questions that have already been asked.
Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about employee healthcare plans and the employee handbook.
You have access to Azure Cognitive Search index with 100's of documents.
Generate a search query based on the conversation and the new question.
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Do not include any special characters like '+'.
If the question is not in English, translate the question to English before generating the search query.
If you cannot generate a search query, return just the number 0.
"""
    query_prompt_few_shots = [
        {"role": USER, "content": "What are my health plans?"},
        {"role": ASSISTANT, "content": "Show available health plans"},
        {"role": USER, "content": "does my plan cover cardio?"},
        {"role": ASSISTANT, "content": "Health plan cardio coverage"},
    ]

    def __init__(self, system_prompt):
        super(StateTypeOpenAI, self).__init__(is_wait_for_user_input_before_state = True)
        self.system_prompt = system_prompt

    async def run(self, app_resources: AppResources, session_state: Any, request_context: RequestContext) -> AsyncGenerator[dict[str, Any], None]:
        has_text = request_context.overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = request_context.overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if request_context.overrides.get("semantic_captions") and has_text else False
        top = request_context.overrides.get("top", 3)
        filter = Utils.build_filter(request_context.overrides, request_context.auth_claims)

        original_user_query = request_context.history[-1]["content"]
        user_query_request = "Generate search query for: " + original_user_query

        functions = [
            {
                "name": "search_sources",
                "description": "Retrieve sources from the Azure Cognitive Search index",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Query string to retrieve documents from azure search eg: 'Health care plan'",
                        }
                    },
                    "required": ["search_query"],
                },
            }
        ]

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        messages = self.get_messages_from_history(
            system_prompt=self.query_prompt_template,
            model_id=app_resources.chatgpt_model,
            history=request_context.history,
            user_content=user_query_request,
            max_tokens=app_resources.chatgpt_token_limit - len(user_query_request),
            few_shots=self.query_prompt_few_shots,
        )

        chatgpt_args = {"deployment_id": app_resources.chatgpt_deployment} if app_resources.openai_host == "azure" else {}
        chat_completion = await openai.ChatCompletion.acreate(
            **chatgpt_args,
            model=app_resources.chatgpt_model,
            messages=messages,
            temperature=0.0,
            max_tokens=100,  # Setting too low risks malformed JSON, setting too high may affect performance
            n=1,
            functions=functions,
            function_call="auto",
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        content = ""
        results = []
        if os.environ["SHOULD_RAG"] == 'True':

            # If retrieval mode includes vectors, compute an embedding for the query
            if has_vector:
                embedding_args = {"deployment_id": app_resources.embedding_deployment} if app_resources.openai_host == "azure" else {}
                embedding = await openai.Embedding.acreate(**embedding_args, model=app_resources.embedding_model, input=query_text)
                query_vector = embedding["data"][0]["embedding"]
            else:
                query_vector = None

            # Only keep the text query if the retrieval mode uses text, otherwise drop it
            if not has_text:
                query_text = None

            # Use semantic L2 reranker if requested and if retrieval mode is text or hybrid (vectors + text)
            if request_context.overrides.get("semantic_ranker") and has_text:
                r = await app_resources.search_client.search(
                    query_text,
                    filter=filter,
                    query_type=QueryType.SEMANTIC,
                    query_language=app_resources.query_language,
                    query_speller=app_resources.query_speller,
                    semantic_configuration_name="default",
                    top=top,
                    query_caption="extractive|highlight-false" if use_semantic_captions else None,
                    vector=query_vector,
                    top_k=50 if query_vector else None,
                    vector_fields="embedding" if query_vector else None,
                )
            else:
                r = await app_resources.search_client.search(
                    query_text,
                    filter=filter,
                    top=top,
                    vector=query_vector,
                    top_k=50 if query_vector else None,
                    vector_fields="embedding" if query_vector else None,
                )
            if use_semantic_captions:
                results = [
                    doc[app_resources.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc["@search.captions"]]))
                    async for doc in r
                ]
            else:
                results = [doc[app_resources.sourcepage_field] + ": " + nonewlines(doc[app_resources.content_field]) async for doc in r]
            content = "\n".join(results)


            
        follow_up_questions_prompt = (
            app_resources.follow_up_questions_prompt_content if request_context.overrides.get("suggest_followup_questions") else ""
        )

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = request_context.overrides.get("prompt_template")
        if prompt_override is None:
            system_message = self.system_prompt.format(
                injected_prompt="", follow_up_questions_prompt=follow_up_questions_prompt
            )
        elif prompt_override.startswith(">>>"):
            system_message = self.system_prompt.format(
                injected_prompt=prompt_override[3:] + "\n", follow_up_questions_prompt=follow_up_questions_prompt
            )
        else:
            system_message = prompt_override.format(follow_up_questions_prompt=follow_up_questions_prompt)

        response_token_limit = 1024
        messages_token_limit = app_resources.chatgpt_token_limit - response_token_limit
        messages = self.get_messages_from_history(
            system_prompt=system_message,
            model_id=app_resources.chatgpt_model,
            history=request_context.history,
            # Model does not handle lengthy system messages well. Moving sources to latest user conversation to solve follow up questions prompt.
            user_content=original_user_query + "\n\nSources:\n" + content,
            max_tokens=messages_token_limit,
        )
        msg_to_display = "\n\n".join([str(message) for message in messages])
        
        extra_info = {
            "data_points": results,
            "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>"
            + msg_to_display.replace("\n", "<br>"),
        }

        chat_coroutine = await openai.ChatCompletion.acreate(
            **chatgpt_args,
            model=app_resources.chatgpt_model,
            messages=messages,
            temperature=request_context.overrides.get("temperature") or 0.7,
            max_tokens=response_token_limit,
            n=1,
            stream=request_context.should_stream,
        )

        request_context.set_response_extra_info(extra_info)
        return self.workaround_first_empty_choices(chat_coroutine)

    def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: list[dict[str, str]],
        user_content: str,
        max_tokens: int,
        few_shots=[],
    ) -> list:
        message_builder = MessageBuilder(system_prompt, model_id)

        # Add examples to show the chat what responses we want. It will try to mimic any responses and make sure they match the rules laid out in the system message.
        for shot in few_shots:
            message_builder.append_message(shot.get("role"), shot.get("content"))

        append_index = len(few_shots) + 1

        message_builder.append_message(self.USER, user_content, index=append_index)
        total_token_count = message_builder.count_tokens_for_message(message_builder.messages[-1])

        newest_to_oldest = list(reversed(history[:-1]))
        for message in newest_to_oldest:
            potential_message_count = message_builder.count_tokens_for_message(message)
            if (total_token_count + potential_message_count) > max_tokens:
                logging.debug("Reached max tokens of %d, history will be truncated", max_tokens)
                break
            message_builder.append_message(message["role"], message["content"], index=append_index)
            total_token_count += potential_message_count
        return message_builder.messages

    def get_search_query(self, chat_completion: dict[str, Any], user_query: str):
        response_message = chat_completion["choices"][0]["message"]
        if function_call := response_message.get("function_call"):
            if function_call["name"] == "search_sources":
                arg = json.loads(function_call["arguments"])
                search_query = arg.get("search_query", self.NO_RESPONSE)
                if search_query != self.NO_RESPONSE:
                    return search_query
        elif query_text := response_message.get("content"):
            if query_text.strip() != self.NO_RESPONSE:
                return query_text
        return user_query

    async def workaround_first_empty_choices(self, chat_coroutine):
        async for event in chat_coroutine:
            # "2023-07-01-preview" API version has a bug where first response has empty choices
            if event["choices"]:
                yield event
