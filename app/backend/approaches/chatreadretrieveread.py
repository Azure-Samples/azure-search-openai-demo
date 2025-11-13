import json
import re
from collections.abc import AsyncGenerator, Awaitable
from typing import Any, Optional, Union, cast

from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

from approaches.approach import (
    Approach,
    ExtraInfo,
    ThoughtStep,
    DataPoints,
)
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager
from prepdocslib.embeddings import ImageEmbeddings
from config import ENABLE_WEB_SEARCH, SERPER_API_KEY, WEB_CACHE_TTL_S, CONFIG_CACHE
from typing import List, Dict
from quart import current_app
import hashlib
import json


class ChatReadRetrieveReadApproach(Approach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    NO_RESPONSE = "0"

    def __init__(
        self,
        *,
        search_client: SearchClient,
        search_index_name: str,
        agent_model: Optional[str],
        agent_deployment: Optional[str],
        agent_client: KnowledgeAgentRetrievalClient,
        auth_helper: AuthenticationHelper,
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
        embedding_router: Optional[Any] = None,
        patentsberta_embeddings: Optional[Any] = None,
        nomic_embeddings: Optional[Any] = None,
    ):
        # Get openai_host from environment or default to "azure"
        import os
        from prepdocslib.strategy import OpenAIHost
        openai_host_str = os.getenv("OPENAI_HOST", "azure")
        openai_host = OpenAIHost(openai_host_str).value if hasattr(OpenAIHost, openai_host_str.upper()) else openai_host_str
        
        super().__init__(
            search_client=search_client,
            openai_client=openai_client,
            auth_helper=auth_helper,
            query_language=query_language,
            query_speller=query_speller,
            embedding_deployment=embedding_deployment,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            embedding_field=embedding_field,
            openai_host=openai_host,
            prompt_manager=prompt_manager,
            reasoning_effort=reasoning_effort,
            multimodal_enabled=multimodal_enabled,
            image_embeddings_client=image_embeddings_client,
            global_blob_manager=global_blob_manager,
            user_blob_manager=user_blob_manager,
            embedding_router=embedding_router,
            patentsberta_embeddings=patentsberta_embeddings,
            nomic_embeddings=nomic_embeddings,
        )
        self.search_client = search_client
        self.search_index_name = search_index_name
        self.agent_model = agent_model
        self.agent_deployment = agent_deployment
        self.agent_client = agent_client
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.prompt_manager = prompt_manager
        self.query_rewrite_prompt = self.prompt_manager.load_prompt("chat_query_rewrite.prompty")
        self.query_rewrite_tools = self.prompt_manager.load_tools("chat_query_rewrite_tools.json")
        self.answer_prompt = self.prompt_manager.load_prompt("chat_answer_question.prompty")
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True
        self.multimodal_enabled = multimodal_enabled
        self.image_embeddings_client = image_embeddings_client
        self.global_blob_manager = global_blob_manager
        self.user_blob_manager = user_blob_manager

    def get_search_query(self, chat_completion: ChatCompletion, user_query: str):
        response_message = chat_completion.choices[0].message

        if response_message.tool_calls:
            for tool in response_message.tool_calls:
                if tool.type != "function":
                    continue
                function = tool.function
                if function.name == "search_sources":
                    arg = json.loads(function.arguments)
                    search_query = arg.get("search_query", self.NO_RESPONSE)
                    if search_query != self.NO_RESPONSE:
                        return search_query
        elif query_text := response_message.content:
            if query_text.strip() != self.NO_RESPONSE:
                return query_text
        return user_query

    def extract_followup_questions(self, content: Optional[str]):
        if content is None:
            return content, []
        return content.split("<<")[0], re.findall(r"<<([^>>]+)>>", content)

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
        
        # Filter citations to only include those actually used in the answer
        from services.citation_filter import filter_citations_by_answer
        if extra_info.data_points.citations and content:
            filtered_citations = filter_citations_by_answer(
                extra_info.data_points.citations,
                content
            )
            extra_info.data_points.citations = filtered_citations
        
        # Assume last thought is for generating answer
        if self.include_token_usage and extra_info.thoughts and chat_completion_response.usage:
            extra_info.thoughts[-1].update_token_usage(chat_completion_response.usage)
        chat_app_response = {
            "message": {"content": content, "role": role},
            "context": extra_info,
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
        chat_coroutine = cast(Awaitable[AsyncStream[ChatCompletionChunk]], chat_coroutine)
        yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}

        followup_questions_started = False
        followup_content = ""
        async for event_chunk in await chat_coroutine:
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
                content = completion["delta"].get("content")
                content = content or ""  # content may either not exist in delta, or explicitly be None
                if overrides.get("suggest_followup_questions") and "<<" in content:
                    followup_questions_started = True
                    earlier_content = content[: content.index("<<")]
                    if earlier_content:
                        completion["delta"]["content"] = earlier_content
                        yield completion
                    followup_content += content[content.index("<<") :]
                elif followup_questions_started:
                    followup_content += content
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
    ) -> tuple[ExtraInfo, Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]]]:
        use_agentic_retrieval = True if overrides.get("use_agentic_retrieval") else False
        original_user_query = messages[-1]["content"]

        reasoning_model_support = self.GPT_REASONING_MODELS.get(self.chatgpt_model)
        if reasoning_model_support and (not reasoning_model_support.streaming and should_stream):
            raise Exception(
                f"{self.chatgpt_model} does not support streaming. Please use a different model or disable streaming."
            )
        if use_agentic_retrieval:
            extra_info = await self.run_agentic_retrieval_approach(messages, overrides, auth_claims)
        else:
            extra_info = await self.run_search_approach(messages, overrides, auth_claims)

        messages = self.prompt_manager.render_prompt(
            self.answer_prompt,
            self.get_system_prompt_variables(overrides.get("prompt_template"))
            | {
                "include_follow_up_questions": bool(overrides.get("suggest_followup_questions")),
                "past_messages": messages[:-1],
                "user_query": original_user_query,
                "text_sources": extra_info.data_points.text,
                "image_sources": extra_info.data_points.images,
                "citations": extra_info.data_points.citations,
            },
        )

        chat_coroutine = cast(
            Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]],
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
        # Phase 1B scaffolding: allow a simple 'mode' switch with safe defaults
        # Default to hybrid mode if web search is enabled, otherwise use rag
        default_mode = "hybrid" if ENABLE_WEB_SEARCH and SERPER_API_KEY else "rag"
        mode = overrides.get("mode", default_mode)  # rag | web | hybrid
        
        # Hybrid mode: merge RAG + Web results
        if mode == "hybrid":
            if not ENABLE_WEB_SEARCH:
                # Fallback to RAG-only if web search disabled
                mode = "rag"
            else:
                # Run both RAG and Web in parallel, then merge
                import asyncio
                from services.web_search.serper_client import SerperClient
                from services.web_search.normalizer import normalize_serper
                
                original_user_query = messages[-1]["content"]
                if not isinstance(original_user_query, str):
                    raise ValueError("The most recent message content must be a string.")
                
                # Get query for web search
                query_messages = self.prompt_manager.render_prompt(
                    self.query_rewrite_prompt, {"user_query": original_user_query, "past_messages": messages[:-1]}
                )
                tools: list[ChatCompletionToolParam] = self.query_rewrite_tools
                chat_completion = cast(
                    ChatCompletion,
                    await self.create_chat_completion(
                        self.chatgpt_deployment,
                        self.chatgpt_model,
                        messages=query_messages,
                        overrides=overrides,
                        response_token_limit=self.get_response_token_limit(self.chatgpt_model, 100),
                        temperature=0.0,
                        tools=tools,
                        reasoning_effort=self.get_lowest_reasoning_effort(self.chatgpt_model),
                    ),
                )
                query_text = self.get_search_query(chat_completion, original_user_query)
                
                # Run RAG search (reuse existing logic but with mode=rag override)
                rag_overrides = {**overrides, "mode": "rag"}
                rag_info = await self.run_search_approach(messages, rag_overrides, auth_claims)
                
                # Run web search with caching
                web_info = None
                if SERPER_API_KEY:
                    try:
                        top = overrides.get("top", 3)
                        
                        # Check cache first
                        cache = current_app.config.get(CONFIG_CACHE)
                        raw_items = None
                        if cache:
                            # Create cache key from query and top parameter
                            cache_key_data = {"query": query_text, "top": top, "provider": "serper"}
                            cache_key = f"web_search:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
                            cached_result = await cache.get(cache_key)
                            if cached_result:
                                raw_items = cached_result
                        
                        # If not in cache, fetch from API
                        if raw_items is None:
                            raw_items = await SerperClient(SERPER_API_KEY).search(query_text, top)
                            # Cache the result
                            if cache:
                                cache_key_data = {"query": query_text, "top": top, "provider": "serper"}
                                cache_key = f"web_search:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
                                await cache.set(cache_key, raw_items, WEB_CACHE_TTL_S)
                        
                        normalized = normalize_serper(raw_items)
                        web_text_sources = [f"{item.get('url','')}: {item.get('snippet','')}" for item in normalized]
                        web_citations = [item.get("url", "") for item in normalized]
                        
                        # Build unified citations for web
                        from services.citation_builder import build_unified_from_text_sources
                        web_text_sources_for_cit = [{"url": item.get("url"), "title": item.get("title"), "content": item.get("snippet"), "sourcefile": item.get("url")} for item in normalized]
                        web_unified = build_unified_from_text_sources(web_text_sources_for_cit)
                        for cit in web_unified:
                            cit["source"] = "web"
                            cit["provider"] = "serper"
                        
                        web_info = ExtraInfo(
                            DataPoints(text=web_text_sources, images=[], citations=web_citations),
                            unified_citations=web_unified,
                        )
                    except Exception as e:
                        # Web search failed, continue with RAG only
                        pass
                
                # Merge RAG + Web results with deduplication
                merged_text = list(rag_info.data_points.text or [])
                merged_citations = list(rag_info.data_points.citations or [])
                merged_unified = list(rag_info.unified_citations or [])
                seen_urls = set()
                
                # Add RAG URLs to seen set
                for cit in rag_info.data_points.citations or []:
                    seen_urls.add(cit.lower())
                
                # Add web results (deduplicate by URL)
                if web_info:
                    for text_src in web_info.data_points.text or []:
                        # Extract URL from text source
                        if "http" in text_src:
                            url = text_src.split(":")[0] if ":" in text_src else ""
                            if url.lower() not in seen_urls:
                                merged_text.append(text_src)
                                seen_urls.add(url.lower())
                    
                    for cit in web_info.data_points.citations or []:
                        if cit.lower() not in seen_urls:
                            merged_citations.append(cit)
                            seen_urls.add(cit.lower())
                    
                    # Merge unified citations
                    merged_unified.extend(web_info.unified_citations or [])
                
                return ExtraInfo(
                    DataPoints(text=merged_text, images=rag_info.data_points.images, citations=merged_citations),
                    thoughts=rag_info.thoughts + [
                        ThoughtStep(
                            title="Hybrid mode (RAG + Web)",
                            description=f"Merged {len(rag_info.data_points.text or [])} RAG + {len(web_info.data_points.text or []) if web_info else 0} web results",
                            props={"mode": "hybrid"},
                        )
                    ],
                    unified_citations=merged_unified,
                )
        
        if mode == "web":
            if not ENABLE_WEB_SEARCH:
                # Web search is disabled; return empty data points but do not crash
                return ExtraInfo(
                    DataPoints(text=[], images=[], citations=[]),
                    thoughts=[
                        ThoughtStep(
                            title="Web search disabled",
                            description="ENABLE_WEB_SEARCH flag is false; returning no external results.",
                            props={"mode": mode},
                        )
                    ],
                )

            # Generate a query (reuse the standard rewrite step for consistency)
            original_user_query = messages[-1]["content"]
            if not isinstance(original_user_query, str):
                raise ValueError("The most recent message content must be a string.")

            query_messages = self.prompt_manager.render_prompt(
                self.query_rewrite_prompt, {"user_query": original_user_query, "past_messages": messages[:-1]}
            )
            tools: list[ChatCompletionToolParam] = self.query_rewrite_tools
            chat_completion = cast(
                ChatCompletion,
                await self.create_chat_completion(
                    self.chatgpt_deployment,
                    self.chatgpt_model,
                    messages=query_messages,
                    overrides=overrides,
                    response_token_limit=self.get_response_token_limit(self.chatgpt_model, 100),
                    temperature=0.0,
                    tools=tools,
                    reasoning_effort=self.get_lowest_reasoning_effort(self.chatgpt_model),
                ),
            )
            query_text = self.get_search_query(chat_completion, original_user_query)

            # Call SERPER and normalize results
            if not SERPER_API_KEY:
                return ExtraInfo(
                    DataPoints(text=[], images=[], citations=[]),
                    thoughts=[
                        ThoughtStep(
                            title="Missing SERPER_API_KEY",
                            description="Set SERPER_API_KEY to enable web search.",
                            props={"mode": mode},
                        )
                    ],
                )

            try:
                from services.web_search.serper_client import SerperClient
                from services.web_search.normalizer import normalize_serper

                top = overrides.get("top", 3)
                
                # Check cache first
                cache = current_app.config.get(CONFIG_CACHE)
                raw_items = None
                if cache:
                    # Create cache key from query and top parameter
                    cache_key_data = {"query": query_text, "top": top, "provider": "serper"}
                    cache_key = f"web_search:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
                    cached_result = await cache.get(cache_key)
                    if cached_result:
                        raw_items = cached_result
                
                # If not in cache, fetch from API
                if raw_items is None:
                    raw_items: List[Dict[str, Any]] = await SerperClient(SERPER_API_KEY).search(query_text, top)
                    # Cache the result
                    if cache:
                        cache_key_data = {"query": query_text, "top": top, "provider": "serper"}
                        cache_key = f"web_search:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
                        await cache.set(cache_key, raw_items, WEB_CACHE_TTL_S)
                
                normalized = normalize_serper(raw_items)

                # Build DataPoints from normalized results
                text_sources = [f"{item.get('url','')}: {item.get('snippet','')}" for item in normalized]
                citations = [item.get("url", "") for item in normalized]

                # Build unified citations from web results
                from services.citation_builder import build_unified_from_text_sources
                # Convert normalized web results to text_sources format for citation builder
                web_text_sources = [{"url": item.get("url"), "title": item.get("title"), "content": item.get("snippet"), "sourcefile": item.get("url")} for item in normalized]
                unified_citations = build_unified_from_text_sources(web_text_sources)
                # Mark as web sources
                for cit in unified_citations:
                    cit["source"] = "web"
                    cit["provider"] = "serper"

                return ExtraInfo(
                    DataPoints(text=text_sources, images=[], citations=citations),
                    thoughts=[
                        ThoughtStep(
                            title="Web search (SERPER)",
                            description=f"Query: {query_text}",
                            props={"top": top, "results": len(normalized)},
                        )
                    ],
                    unified_citations=unified_citations,
                )
            except Exception as e:
                return ExtraInfo(
                    DataPoints(text=[], images=[], citations=[]),
                    thoughts=[
                        ThoughtStep(
                            title="Web search error",
                            description=str(e),
                            props={"mode": mode},
                        )
                    ],
                )

        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        use_query_rewriting = True if overrides.get("query_rewriting") else False
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        search_index_filter = self.build_filter(overrides, auth_claims)
        send_text_sources = overrides.get("send_text_sources", True)
        send_image_sources = overrides.get("send_image_sources", self.multimodal_enabled) and self.multimodal_enabled
        search_text_embeddings = overrides.get("search_text_embeddings", True)
        search_image_embeddings = (
            overrides.get("search_image_embeddings", self.multimodal_enabled) and self.multimodal_enabled
        )

        original_user_query = messages[-1]["content"]
        if not isinstance(original_user_query, str):
            raise ValueError("The most recent message content must be a string.")

        query_messages = self.prompt_manager.render_prompt(
            self.query_rewrite_prompt, {"user_query": original_user_query, "past_messages": messages[:-1]}
        )
        tools: list[ChatCompletionToolParam] = self.query_rewrite_tools

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question

        chat_completion = cast(
            ChatCompletion,
            await self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages=query_messages,
                overrides=overrides,
                response_token_limit=self.get_response_token_limit(
                    self.chatgpt_model, 100
                ),  # Setting too low risks malformed JSON, setting too high may affect performance
                temperature=0.0,  # Minimize creativity for search query generation
                tools=tools,
                reasoning_effort=self.get_lowest_reasoning_effort(self.chatgpt_model),
            ),
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

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
        )

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        data_points = await self.get_sources_content(
            results,
            use_semantic_captions,
            include_text_sources=send_text_sources,
            download_image_sources=send_image_sources,
            user_oid=auth_claims.get("oid"),
        )
        
        # Build unified citations from RAG results
        from services.citation_builder import build_unified_from_text_sources
        # Convert Document results to text_sources format
        rag_text_sources = [{"sourcepage": doc.sourcepage, "sourcefile": doc.sourcefile, "title": doc.sourcefile or "Document", "content": doc.content or ""} for doc in results]
        unified_citations = build_unified_from_text_sources(rag_text_sources)
        
        extra_info = ExtraInfo(
            data_points,
            thoughts=[
                self.format_thought_step_for_chatcompletion(
                    title="Prompt to generate search query",
                    messages=query_messages,
                    overrides=overrides,
                    model=self.chatgpt_model,
                    deployment=self.chatgpt_deployment,
                    usage=chat_completion.usage,
                    reasoning_effort=self.get_lowest_reasoning_effort(self.chatgpt_model),
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
            unified_citations=unified_citations,
        )
        return extra_info

    async def run_agentic_retrieval_approach(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
    ):
        search_index_filter = self.build_filter(overrides, auth_claims)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0)
        top = overrides.get("top", 3)
        results_merge_strategy = overrides.get("results_merge_strategy", "interleaved")
        send_text_sources = overrides.get("send_text_sources", True)
        send_image_sources = overrides.get("send_image_sources", self.multimodal_enabled) and self.multimodal_enabled

        response, results = await self.run_agentic_retrieval(
            messages=messages,
            agent_client=self.agent_client,
            search_index_name=self.search_index_name,
            top=top,
            filter_add_on=search_index_filter,
            minimum_reranker_score=minimum_reranker_score,
            results_merge_strategy=results_merge_strategy,
        )

        data_points = await self.get_sources_content(
            results,
            use_semantic_captions=False,
            include_text_sources=send_text_sources,
            download_image_sources=send_image_sources,
            user_oid=auth_claims.get("oid"),
        )
        extra_info = ExtraInfo(
            data_points,
            thoughts=[
                ThoughtStep(
                    "Use agentic retrieval",
                    messages,
                    {
                        "reranker_threshold": minimum_reranker_score,
                        "results_merge_strategy": results_merge_strategy,
                        "filter": search_index_filter,
                    },
                ),
                ThoughtStep(
                    f"Agentic retrieval results (top {top})",
                    [result.serialize_for_results() for result in results],
                    {
                        "query_plan": (
                            [activity.as_dict() for activity in response.activity] if response.activity else None
                        ),
                        "model": self.agent_model,
                        "deployment": self.agent_deployment,
                    },
                ),
            ],
        )
        return extra_info
