import os
from abc import ABC
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypedDict, Union, cast
from urllib.parse import urljoin

import aiohttp
from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentAzureSearchDocReference,
    KnowledgeAgentIndexParams,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentRetrievalResponse,
    KnowledgeAgentSearchActivityRecord,
)
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import (
    QueryCaptionResult,
    QueryType,
    VectorizedQuery,
    VectorQuery,
)
from openai import AsyncOpenAI, AsyncStream
from openai.types import CompletionUsage
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionReasoningEffort,
    ChatCompletionToolParam,
)

from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper


@dataclass
class Document:
    id: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    sourcepage: Optional[str] = None
    sourcefile: Optional[str] = None
    oids: Optional[list[str]] = None
    groups: Optional[list[str]] = None
    captions: Optional[list[QueryCaptionResult]] = None
    score: Optional[float] = None
    reranker_score: Optional[float] = None
    search_agent_query: Optional[str] = None

    def serialize_for_results(self) -> dict[str, Any]:
        result_dict = {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "sourcepage": self.sourcepage,
            "sourcefile": self.sourcefile,
            "oids": self.oids,
            "groups": self.groups,
            "captions": (
                [
                    {
                        "additional_properties": caption.additional_properties,
                        "text": caption.text,
                        "highlights": caption.highlights,
                    }
                    for caption in self.captions
                ]
                if self.captions
                else []
            ),
            "score": self.score,
            "reranker_score": self.reranker_score,
            "search_agent_query": self.search_agent_query,
        }
        return result_dict


@dataclass
class ThoughtStep:
    title: str
    description: Optional[Any]
    props: Optional[dict[str, Any]] = None

    def update_token_usage(self, usage: CompletionUsage) -> None:
        if self.props:
            self.props["token_usage"] = TokenUsageProps.from_completion_usage(usage)


@dataclass
class DataPoints:
    text: Optional[list[str]] = None
    images: Optional[list] = None


@dataclass
class ExtraInfo:
    data_points: DataPoints
    thoughts: Optional[list[ThoughtStep]] = None
    followup_questions: Optional[list[Any]] = None


@dataclass
class TokenUsageProps:
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: Optional[int]
    total_tokens: int

    @classmethod
    def from_completion_usage(cls, usage: CompletionUsage) -> "TokenUsageProps":
        return cls(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            reasoning_tokens=(
                usage.completion_tokens_details.reasoning_tokens if usage.completion_tokens_details else None
            ),
            total_tokens=usage.total_tokens,
        )


# GPT reasoning models don't support the same set of parameters as other models
# https://learn.microsoft.com/azure/ai-services/openai/how-to/reasoning
@dataclass
class GPTReasoningModelSupport:
    streaming: bool
    minimal_effort: bool


class Approach(ABC):
    # List of GPT reasoning models support
    GPT_REASONING_MODELS = {
        "o1": GPTReasoningModelSupport(streaming=False, minimal_effort=False),
        "o3": GPTReasoningModelSupport(streaming=True, minimal_effort=False),
        "o3-mini": GPTReasoningModelSupport(streaming=True, minimal_effort=False),
        "o4-mini": GPTReasoningModelSupport(streaming=True, minimal_effort=False),
        "gpt-5": GPTReasoningModelSupport(streaming=True, minimal_effort=True),
        "gpt-5-nano": GPTReasoningModelSupport(streaming=True, minimal_effort=True),
        "gpt-5-mini": GPTReasoningModelSupport(streaming=True, minimal_effort=True),
    }
    # Set a higher token limit for GPT reasoning models
    RESPONSE_DEFAULT_TOKEN_LIMIT = 1024
    RESPONSE_REASONING_DEFAULT_TOKEN_LIMIT = 8192

    def __init__(
        self,
        search_client: SearchClient,
        openai_client: AsyncOpenAI,
        auth_helper: AuthenticationHelper,
        query_language: Optional[str],
        query_speller: Optional[str],
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        embedding_dimensions: int,
        embedding_field: str,
        openai_host: str,
        vision_endpoint: str,
        vision_token_provider: Callable[[], Awaitable[str]],
        prompt_manager: PromptManager,
        reasoning_effort: Optional[str] = None,
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.query_language = query_language
        self.query_speller = query_speller
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.embedding_field = embedding_field
        self.openai_host = openai_host
        self.vision_endpoint = vision_endpoint
        self.vision_token_provider = vision_token_provider
        self.prompt_manager = prompt_manager
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True

    def build_filter(self, overrides: dict[str, Any], auth_claims: dict[str, Any]) -> Optional[str]:
        include_category = overrides.get("include_category")
        exclude_category = overrides.get("exclude_category")
        security_filter = self.auth_helper.build_security_filters(overrides, auth_claims)
        filters = []
        if include_category:
            filters.append("category eq '{}'".format(include_category.replace("'", "''")))
        if exclude_category:
            filters.append("category ne '{}'".format(exclude_category.replace("'", "''")))
        if security_filter:
            filters.append(security_filter)
        return None if len(filters) == 0 else " and ".join(filters)

    async def search(
        self,
        top: int,
        query_text: Optional[str],
        filter: Optional[str],
        vectors: list[VectorQuery],
        use_text_search: bool,
        use_vector_search: bool,
        use_semantic_ranker: bool,
        use_semantic_captions: bool,
        minimum_search_score: Optional[float] = None,
        minimum_reranker_score: Optional[float] = None,
        use_query_rewriting: Optional[bool] = None,
    ) -> list[Document]:
        search_text = query_text if use_text_search else ""
        search_vectors = vectors if use_vector_search else []
        if use_semantic_ranker:
            results = await self.search_client.search(
                search_text=search_text,
                filter=filter,
                top=top,
                query_caption="extractive|highlight-false" if use_semantic_captions else None,
                query_rewrites="generative" if use_query_rewriting else None,
                vector_queries=search_vectors,
                query_type=QueryType.SEMANTIC,
                query_language=self.query_language,
                query_speller=self.query_speller,
                semantic_configuration_name="default",
                semantic_query=query_text,
            )
        else:
            results = await self.search_client.search(
                search_text=search_text,
                filter=filter,
                top=top,
                vector_queries=search_vectors,
            )

        documents = []
        async for page in results.by_page():
            async for document in page:
                documents.append(
                    Document(
                        id=document.get("id"),
                        content=document.get("content"),
                        category=document.get("category"),
                        sourcepage=document.get("sourcepage"),
                        sourcefile=document.get("sourcefile"),
                        oids=document.get("oids"),
                        groups=document.get("groups"),
                        captions=cast(list[QueryCaptionResult], document.get("@search.captions")),
                        score=document.get("@search.score"),
                        reranker_score=document.get("@search.reranker_score"),
                    )
                )

            qualified_documents = [
                doc
                for doc in documents
                if (
                    (doc.score or 0) >= (minimum_search_score or 0)
                    and (doc.reranker_score or 0) >= (minimum_reranker_score or 0)
                )
            ]

        return qualified_documents

    async def run_agentic_retrieval(
        self,
        messages: list[ChatCompletionMessageParam],
        agent_client: KnowledgeAgentRetrievalClient,
        search_index_name: str,
        top: Optional[int] = None,
        filter_add_on: Optional[str] = None,
        minimum_reranker_score: Optional[float] = None,
        max_docs_for_reranker: Optional[int] = None,
        results_merge_strategy: Optional[str] = None,
    ) -> tuple[KnowledgeAgentRetrievalResponse, list[Document]]:
        # STEP 1: Invoke agentic retrieval
        response = await agent_client.retrieve(
            retrieval_request=KnowledgeAgentRetrievalRequest(
                messages=[
                    KnowledgeAgentMessage(
                        role=str(msg["role"]), content=[KnowledgeAgentMessageTextContent(text=str(msg["content"]))]
                    )
                    for msg in messages
                    if msg["role"] != "system"
                ],
                target_index_params=[
                    KnowledgeAgentIndexParams(
                        index_name=search_index_name,
                        reranker_threshold=minimum_reranker_score,
                        max_docs_for_reranker=max_docs_for_reranker,
                        filter_add_on=filter_add_on,
                        include_reference_source_data=True,
                    )
                ],
            )
        )

        # STEP 2: Generate a contextual and content specific answer using the search results and chat history
        activities = response.activity
        activity_mapping = (
            {
                activity.id: activity.query.search if activity.query else ""
                for activity in activities
                if isinstance(activity, KnowledgeAgentSearchActivityRecord)
            }
            if activities
            else {}
        )

        results = []
        if response and response.references:
            if results_merge_strategy == "interleaved":
                # Use interleaved reference order
                references = sorted(response.references, key=lambda reference: int(reference.id))
            else:
                # Default to descending strategy
                references = response.references
            for reference in references:
                if isinstance(reference, KnowledgeAgentAzureSearchDocReference) and reference.source_data:
                    results.append(
                        Document(
                            id=reference.doc_key,
                            content=reference.source_data["content"],
                            sourcepage=reference.source_data["sourcepage"],
                            search_agent_query=activity_mapping[reference.activity_source],
                        )
                    )
                if top and len(results) == top:
                    break

        return response, results

    def get_sources_content(
        self, results: list[Document], use_semantic_captions: bool, use_image_citation: bool
    ) -> list[str]:

        def nonewlines(s: str) -> str:
            return s.replace("\n", " ").replace("\r", " ")

        if use_semantic_captions:
            return [
                (self.get_citation((doc.sourcepage or ""), use_image_citation))
                + ": "
                + nonewlines(" . ".join([cast(str, c.text) for c in (doc.captions or [])]))
                for doc in results
            ]
        else:
            return [
                (self.get_citation((doc.sourcepage or ""), use_image_citation)) + ": " + nonewlines(doc.content or "")
                for doc in results
            ]

    def get_citation(self, sourcepage: str, use_image_citation: bool) -> str:
        if use_image_citation:
            return sourcepage
        else:
            path, ext = os.path.splitext(sourcepage)
            if ext.lower() == ".png":
                page_idx = path.rfind("-")
                page_number = int(path[page_idx + 1 :])
                return f"{path[:page_idx]}.pdf#page={page_number}"

            return sourcepage

    async def compute_text_embedding(self, q: str):
        SUPPORTED_DIMENSIONS_MODEL = {
            "text-embedding-ada-002": False,
            "text-embedding-3-small": True,
            "text-embedding-3-large": True,
        }

        class ExtraArgs(TypedDict, total=False):
            dimensions: int

        dimensions_args: ExtraArgs = (
            {"dimensions": self.embedding_dimensions} if SUPPORTED_DIMENSIONS_MODEL[self.embedding_model] else {}
        )
        embedding = await self.openai_client.embeddings.create(
            # Azure OpenAI takes the deployment name as the model name
            model=self.embedding_deployment if self.embedding_deployment else self.embedding_model,
            input=q,
            **dimensions_args,
        )
        query_vector = embedding.data[0].embedding
        # This performs an oversampling due to how the search index was setup,
        # so we do not need to explicitly pass in an oversampling parameter here
        return VectorizedQuery(vector=query_vector, k_nearest_neighbors=50, fields=self.embedding_field)

    async def compute_image_embedding(self, q: str):
        endpoint = urljoin(self.vision_endpoint, "computervision/retrieval:vectorizeText")
        headers = {"Content-Type": "application/json"}
        params = {"api-version": "2024-02-01", "model-version": "2023-04-15"}
        data = {"text": q}

        headers["Authorization"] = "Bearer " + await self.vision_token_provider()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=endpoint, params=params, headers=headers, json=data, raise_for_status=True
            ) as response:
                json = await response.json()
                image_query_vector = json["vector"]
        return VectorizedQuery(vector=image_query_vector, k_nearest_neighbors=50, fields="imageEmbedding")

    def get_system_prompt_variables(self, override_prompt: Optional[str]) -> dict[str, str]:
        # Allows client to replace the entire prompt, or to inject into the existing prompt using >>>
        if override_prompt is None:
            return {}
        elif override_prompt.startswith(">>>"):
            return {"injected_prompt": override_prompt[3:]}
        else:
            return {"override_prompt": override_prompt}

    def get_response_token_limit(self, model: str, default_limit: int) -> int:
        if model in self.GPT_REASONING_MODELS:
            return self.RESPONSE_REASONING_DEFAULT_TOKEN_LIMIT

        return default_limit

    def get_lowest_reasoning_effort(self, model: str) -> ChatCompletionReasoningEffort:
        """
        Return the lowest valid reasoning_effort for the given model.
        """
        if model not in self.GPT_REASONING_MODELS:
            return None
        if self.GPT_REASONING_MODELS[model].minimal_effort:
            return "minimal"
        return "low"

    def create_chat_completion(
        self,
        chatgpt_deployment: Optional[str],
        chatgpt_model: str,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        response_token_limit: int,
        should_stream: bool = False,
        tools: Optional[list[ChatCompletionToolParam]] = None,
        temperature: Optional[float] = None,
        n: Optional[int] = None,
        reasoning_effort: Optional[ChatCompletionReasoningEffort] = None,
    ) -> Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]]:
        if chatgpt_model in self.GPT_REASONING_MODELS:
            params: dict[str, Any] = {
                # max_tokens is not supported
                "max_completion_tokens": response_token_limit
            }

            # Adjust parameters for reasoning models
            supported_features = self.GPT_REASONING_MODELS[chatgpt_model]
            if supported_features.streaming and should_stream:
                params["stream"] = True
                params["stream_options"] = {"include_usage": True}
            params["reasoning_effort"] = reasoning_effort or overrides.get("reasoning_effort") or self.reasoning_effort

        else:
            # Include parameters that may not be supported for reasoning models
            params = {
                "max_tokens": response_token_limit,
                "temperature": temperature or overrides.get("temperature", 0.3),
            }
        if should_stream:
            params["stream"] = True
            params["stream_options"] = {"include_usage": True}

        params["tools"] = tools

        # Azure OpenAI takes the deployment name as the model name
        return self.openai_client.chat.completions.create(
            model=chatgpt_deployment if chatgpt_deployment else chatgpt_model,
            messages=messages,
            seed=overrides.get("seed", None),
            n=n or 1,
            **params,
        )

    def format_thought_step_for_chatcompletion(
        self,
        title: str,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        model: str,
        deployment: Optional[str],
        usage: Optional[CompletionUsage] = None,
        reasoning_effort: Optional[ChatCompletionReasoningEffort] = None,
    ) -> ThoughtStep:
        properties: dict[str, Any] = {"model": model}
        if deployment:
            properties["deployment"] = deployment
        # Only add reasoning_effort setting if the model supports it
        if model in self.GPT_REASONING_MODELS:
            properties["reasoning_effort"] = reasoning_effort or overrides.get(
                "reasoning_effort", self.reasoning_effort
            )
        if usage:
            properties["token_usage"] = TokenUsageProps.from_completion_usage(usage)
        return ThoughtStep(title, messages, properties)

    async def run(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def run_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> AsyncGenerator[dict[str, Any], None]:
        raise NotImplementedError
