import re
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import asdict
from typing import Any, Optional, cast

from azure.search.documents.aio import SearchClient
from azure.search.documents.knowledgebases.aio import KnowledgeBaseRetrievalClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from approaches.approach import (
    Approach,
    ExtraInfo,
    ThoughtStep,
)
from approaches.promptmanager import PromptManager
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager
from prepdocslib.embeddings import ImageEmbeddings


class ChatReadRetrieveReadApproach(Approach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    NO_RESPONSE = Approach.QUERY_REWRITE_NO_RESPONSE

    def __init__(
        self,
        *,
        search_client: SearchClient,
        search_index_name: str,
        knowledgebase_model: Optional[str],
        knowledgebase_deployment: Optional[str],
        knowledgebase_client: Optional[KnowledgeBaseRetrievalClient],
        knowledgebase_client_with_web: Optional[KnowledgeBaseRetrievalClient] = None,
        knowledgebase_client_with_sharepoint: Optional[KnowledgeBaseRetrievalClient] = None,
        knowledgebase_client_with_web_and_sharepoint: Optional[KnowledgeBaseRetrievalClient] = None,
        openai_client: AsyncOpenAI,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        embedding_dimensions: int,
        embedding_field: str,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        prompt_manager: PromptManager,
        reasoning_effort: Optional[str] = None,
        multimodal_enabled: bool = False,
        image_embeddings_client: Optional[ImageEmbeddings] = None,
        global_blob_manager: Optional[BlobManager] = None,
        user_blob_manager: Optional[AdlsBlobManager] = None,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False,
        retrieval_reasoning_effort: Optional[str] = None,
    ):
        self.search_client = search_client
        self.search_index_name = search_index_name
        self.knowledgebase_model = knowledgebase_model
        self.knowledgebase_deployment = knowledgebase_deployment
        self.knowledgebase_client = knowledgebase_client
        self.knowledgebase_client_with_web = knowledgebase_client_with_web
        self.knowledgebase_client_with_sharepoint = knowledgebase_client_with_sharepoint
        self.knowledgebase_client_with_web_and_sharepoint = knowledgebase_client_with_web_and_sharepoint
        self.openai_client = openai_client
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.embedding_field = embedding_field
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.prompt_manager = prompt_manager
        self.query_rewrite_tools = self.prompt_manager.load_tools("chat_query_rewrite_tools.json")
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True
        self.multimodal_enabled = multimodal_enabled
        self.image_embeddings_client = image_embeddings_client
        self.global_blob_manager = global_blob_manager
        self.user_blob_manager = user_blob_manager
        # Track whether web source retrieval is enabled for this deployment; overrides may only disable it.
        self.web_source_enabled = use_web_source
        self.use_sharepoint_source = use_sharepoint_source
        self.retrieval_reasoning_effort = retrieval_reasoning_effort

    def extract_followup_questions(self, content: Optional[str]):
        if content is None:
            return content, []
        return content.split("<<")[0], re.findall(r"<<([^>>]+)>>", content)

    def get_search_query(self, chat_completion: ChatCompletion, default_query: str) -> str:
        """Read the optimized search query from a chat completion tool call."""
        try:
            return self.extract_rewritten_query(chat_completion, default_query, no_response_token=self.NO_RESPONSE)
        except Exception:
            return default_query

    async def run_without_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> dict[str, Any]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=False
        )
        chat_completion_response: ChatCompletion = await cast(Awaitable[ChatCompletion], chat_coroutine)
        content = chat_completion_response.choices[0].message.content
        role = chat_completion_response.choices[0].message.role
        if overrides.get("suggest_followup_questions"):
            content, followup_questions = self.extract_followup_questions(content)
            extra_info.followup_questions = followup_questions
        # Assume last thought is for generating answer
        # TODO: Update for agentic? This isn't still true?
        if self.include_token_usage and extra_info.thoughts and chat_completion_response.usage:
            extra_info.thoughts[-1].update_token_usage(chat_completion_response.usage)
        chat_app_response = {
            "message": {"content": content, "role": role},
            "context": {
                "thoughts": extra_info.thoughts,
                "data_points": {
                    key: value for key, value in asdict(extra_info.data_points).items() if value is not None
                },
                "followup_questions": extra_info.followup_questions,
            },
            "session_state": session_state,
        }
        return chat_app_response

    async def run_with_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> AsyncGenerator[dict, None]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=True
        )
        yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}

        followup_questions_started = False
        followup_content = ""
        chat_result = await chat_coroutine

        if isinstance(chat_result, ChatCompletion):
            message = chat_result.choices[0].message
            content = message.content or ""
            role = message.role or "assistant"

            followup_questions: list[str] = []
            if overrides.get("suggest_followup_questions"):
                content, followup_questions = self.extract_followup_questions(content)
                extra_info.followup_questions = followup_questions

            if self.include_token_usage and extra_info.thoughts and chat_result.usage:
                extra_info.thoughts[-1].update_token_usage(chat_result.usage)

            delta_payload: dict[str, Any] = {"role": role}
            if content:
                delta_payload["content"] = content
            yield {"delta": delta_payload}

            yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}

            if followup_questions:
                yield {
                    "delta": {"role": "assistant"},
                    "context": {"context": extra_info, "followup_questions": followup_questions},
                }
            return

        chat_result = cast(AsyncStream[ChatCompletionChunk], chat_result)

        async for event_chunk in chat_result:
            # "2023-07-01-preview" API version has a bug where first response has empty choices
            event = event_chunk.model_dump()  # Convert pydantic model to dict
            if event["choices"]:
                # No usage during streaming
                completion = {
                    "delta": {
                        "content": event["choices"][0]["delta"].get("content"),
                        "role": event["choices"][0]["delta"]["role"],
                    }
                }
                # if event contains << and not >>, it is start of follow-up question, truncate
                delta_content_raw = completion["delta"].get("content")
                delta_content: str = (
                    delta_content_raw or ""
                )  # content may either not exist in delta, or explicitly be None
                if overrides.get("suggest_followup_questions") and "<<" in delta_content:
                    followup_questions_started = True
                    earlier_content = delta_content[: delta_content.index("<<")]
                    if earlier_content:
                        completion["delta"]["content"] = earlier_content
                        yield completion
                    followup_content += delta_content[delta_content.index("<<") :]
                elif followup_questions_started:
                    followup_content += delta_content
                else:
                    yield completion
            else:
                # Final chunk at end of streaming should contain usage
                # https://cookbook.openai.com/examples/how_to_stream_completions#4-how-to-get-token-usage-data-for-streamed-chat-completion-response
                if event_chunk.usage and extra_info.thoughts and self.include_token_usage:
                    extra_info.thoughts[-1].update_token_usage(event_chunk.usage)
                    yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}

        if followup_content:
            _, followup_questions = self.extract_followup_questions(followup_content)
            yield {
                "delta": {"role": "assistant"},
                "context": {"context": extra_info, "followup_questions": followup_questions},
            }

    async def run(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> dict[str, Any]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        return await self.run_without_streaming(messages, overrides, auth_claims, session_state)

    async def run_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> AsyncGenerator[dict[str, Any], None]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        return self.run_with_streaming(messages, overrides, auth_claims, session_state)

    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[ExtraInfo, Awaitable[ChatCompletion] | Awaitable[AsyncStream[ChatCompletionChunk]]]:
        use_agentic_knowledgebase = True if overrides.get("use_agentic_knowledgebase") else False
        original_user_query = messages[-1]["content"]

        reasoning_model_support = self.GPT_REASONING_MODELS.get(self.chatgpt_model)
        if reasoning_model_support and (not reasoning_model_support.streaming and should_stream):
            raise Exception(
                f"{self.chatgpt_model} does not support streaming. Please use a different model or disable streaming."
            )
        if use_agentic_knowledgebase:
            if should_stream and overrides.get("use_web_source"):
                raise Exception(
                    "Streaming is not supported with agentic retrieval when web source is enabled. Please disable streaming or web source."
                )
            extra_info = await self.run_agentic_retrieval_approach(messages, overrides, auth_claims)
        else:
            extra_info = await self.run_search_approach(messages, overrides, auth_claims)

        if extra_info.answer:
            # If agentic retrieval already provided an answer, skip final call to LLM
            async def return_answer() -> ChatCompletion:
                return ChatCompletion(
                    id="no-final-call",
                    object="chat.completion",
                    created=0,
                    model=self.chatgpt_model,
                    choices=[
                        Choice(
                            message=ChatCompletionMessage(
                                role="assistant",
                                content=extra_info.answer,
                            ),
                            finish_reason="stop",
                            index=0,
                        )
                    ],
                )

            return (extra_info, return_answer())

        messages = self.prompt_manager.build_conversation(
            system_template_path="chat_answer.system.jinja2",
            system_template_variables=self.get_system_prompt_variables(overrides.get("prompt_template"))
            | {
                "include_follow_up_questions": bool(overrides.get("suggest_followup_questions")),
                "image_sources": extra_info.data_points.images,
                "citations": extra_info.data_points.citations,
            },
            user_template_path="chat_answer.user.jinja2",
            user_template_variables={
                "user_query": original_user_query,
                "text_sources": extra_info.data_points.text,
            },
            user_image_sources=extra_info.data_points.images,
            past_messages=messages[:-1],
        )

        chat_coroutine = cast(
            Awaitable[ChatCompletion] | Awaitable[AsyncStream[ChatCompletionChunk]],
            self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages,
                overrides,
                self.get_response_token_limit(self.chatgpt_model, 1024),
                should_stream,
            ),
        )
        extra_info.thoughts.append(
            self.format_thought_step_for_chatcompletion(
                title="Prompt to generate answer",
                messages=messages,
                overrides=overrides,
                model=self.chatgpt_model,
                deployment=self.chatgpt_deployment,
                usage=None,
            )
        )
        return (extra_info, chat_coroutine)

    async def run_search_approach(
        self, messages: list[ChatCompletionMessageParam], overrides: dict[str, Any], auth_claims: dict[str, Any]
    ):
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        use_query_rewriting = True if overrides.get("query_rewriting") else False
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        search_index_filter = self.build_filter(overrides)
        access_token = auth_claims.get("access_token")
        send_text_sources = overrides.get("send_text_sources", True)
        send_image_sources = overrides.get("send_image_sources", self.multimodal_enabled) and self.multimodal_enabled
        search_text_embeddings = overrides.get("search_text_embeddings", True)
        search_image_embeddings = (
            overrides.get("search_image_embeddings", self.multimodal_enabled) and self.multimodal_enabled
        )

        original_user_query = messages[-1]["content"]
        if not isinstance(original_user_query, str):
            raise ValueError("The most recent message content must be a string.")

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question

        rewrite_result = await self.rewrite_query(
            prompt_template="query_rewrite.system.jinja2",
            prompt_variables={
                "user_query": original_user_query,
                "past_messages": messages[:-1],
            },
            overrides=overrides,
            chatgpt_model=self.chatgpt_model,
            chatgpt_deployment=self.chatgpt_deployment,
            user_query=original_user_query,
            response_token_limit=self.get_response_token_limit(
                self.chatgpt_model, 100
            ),  # Setting too low risks malformed JSON, setting too high may affect performance
            tools=self.query_rewrite_tools,
            temperature=0.0,  # Minimize creativity for search query generation
            no_response_token=self.NO_RESPONSE,
        )

        query_text = rewrite_result.query

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        vectors: list[VectorQuery] = []
        if use_vector_search:
            if search_text_embeddings:
                vectors.append(await self.compute_text_embedding(query_text))
            if search_image_embeddings:
                vectors.append(await self.compute_multimodal_embedding(query_text))

        results = await self.search(
            top,
            query_text,
            search_index_filter,
            vectors,
            use_text_search,
            use_vector_search,
            use_semantic_ranker,
            use_semantic_captions,
            minimum_search_score,
            minimum_reranker_score,
            use_query_rewriting,
            access_token,
        )

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        data_points = await self.get_sources_content(
            results,
            use_semantic_captions,
            include_text_sources=send_text_sources,
            download_image_sources=send_image_sources,
            user_oid=auth_claims.get("oid"),
        )
        extra_info = ExtraInfo(
            data_points,
            thoughts=[
                self.format_thought_step_for_chatcompletion(
                    title="Prompt to generate search query",
                    messages=rewrite_result.messages,
                    overrides=overrides,
                    model=self.chatgpt_model,
                    deployment=self.chatgpt_deployment,
                    usage=rewrite_result.completion.usage,
                    reasoning_effort=rewrite_result.reasoning_effort,
                ),
                ThoughtStep(
                    "Search using generated search query",
                    query_text,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "use_query_rewriting": use_query_rewriting,
                        "top": top,
                        "filter": search_index_filter,
                        "use_vector_search": use_vector_search,
                        "use_text_search": use_text_search,
                        "search_text_embeddings": search_text_embeddings,
                        "search_image_embeddings": search_image_embeddings,
                    },
                ),
                ThoughtStep(
                    "Search results",
                    [result.serialize_for_results() for result in results],
                ),
            ],
        )
        return extra_info

    async def run_agentic_retrieval_approach(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
    ):
        search_index_filter = self.build_filter(overrides)
        access_token = auth_claims.get("access_token")
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0)
        send_text_sources = overrides.get("send_text_sources", True)
        send_image_sources = overrides.get("send_image_sources", self.multimodal_enabled) and self.multimodal_enabled
        retrieval_reasoning_effort = overrides.get("retrieval_reasoning_effort", self.retrieval_reasoning_effort)
        # Overrides can only disable web source support configured at construction time.
        use_web_source = self.web_source_enabled
        override_use_web_source = overrides.get("use_web_source")
        if isinstance(override_use_web_source, bool):
            use_web_source = use_web_source and override_use_web_source
        # Overrides can only disable sharepoint source support configured at construction time.
        use_sharepoint_source = self.use_sharepoint_source
        override_use_sharepoint_source = overrides.get("use_sharepoint_source")
        if isinstance(override_use_sharepoint_source, bool):
            use_sharepoint_source = use_sharepoint_source and override_use_sharepoint_source
        if use_web_source and retrieval_reasoning_effort == "minimal":
            raise Exception("Web source cannot be used with minimal retrieval reasoning effort.")

        selected_client, effective_web_source, effective_sharepoint_source = self._select_knowledgebase_client(
            use_web_source,
            use_sharepoint_source,
        )

        agentic_results = await self.run_agentic_retrieval(
            messages=messages,
            knowledgebase_client=selected_client,
            search_index_name=self.search_index_name,
            filter_add_on=search_index_filter,
            minimum_reranker_score=minimum_reranker_score,
            access_token=access_token,
            use_web_source=effective_web_source,
            use_sharepoint_source=effective_sharepoint_source,
            retrieval_reasoning_effort=retrieval_reasoning_effort,
        )

        data_points = await self.get_sources_content(
            agentic_results.documents,
            use_semantic_captions=False,
            include_text_sources=send_text_sources,
            download_image_sources=send_image_sources,
            user_oid=auth_claims.get("oid"),
            web_results=agentic_results.web_results,
            sharepoint_results=agentic_results.sharepoint_results,
        )

        return ExtraInfo(
            data_points,
            thoughts=agentic_results.thoughts,
            answer=agentic_results.answer,
        )

    def _select_knowledgebase_client(
        self,
        use_web_source: bool,
        use_sharepoint_source: bool,
    ) -> tuple[KnowledgeBaseRetrievalClient, bool, bool]:
        if use_web_source and use_sharepoint_source:
            if self.knowledgebase_client_with_web_and_sharepoint:
                return self.knowledgebase_client_with_web_and_sharepoint, True, True
            if self.knowledgebase_client_with_web:
                return self.knowledgebase_client_with_web, True, False
            if self.knowledgebase_client_with_sharepoint:
                return self.knowledgebase_client_with_sharepoint, False, True

        if use_web_source and self.knowledgebase_client_with_web:
            return self.knowledgebase_client_with_web, True, False

        if use_sharepoint_source and self.knowledgebase_client_with_sharepoint:
            return self.knowledgebase_client_with_sharepoint, False, True

        if self.knowledgebase_client:
            return self.knowledgebase_client, False, False
        raise ValueError("Agentic retrieval requested but no knowledge base is configured")
