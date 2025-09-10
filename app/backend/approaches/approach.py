import base64
from abc import ABC
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict, Union, cast

from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentRetrievalResponse,
    KnowledgeAgentSearchIndexActivityRecord,
    KnowledgeAgentSearchIndexReference,
    SearchIndexKnowledgeSourceParams,
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
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager
from prepdocslib.embeddings import ImageEmbeddings


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
    images: Optional[list[dict[str, Any]]] = None

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
            "images": self.images,
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
    citations: Optional[list[str]] = None


@dataclass
class ExtraInfo:
    data_points: DataPoints
    thoughts: list[ThoughtStep] = field(default_factory=list)
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
        prompt_manager: PromptManager,
        reasoning_effort: Optional[str] = None,
        multimodal_enabled: bool = False,
        image_embeddings_client: Optional[ImageEmbeddings] = None,
        global_blob_manager: Optional[BlobManager] = None,
        user_blob_manager: Optional[AdlsBlobManager] = None,
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
        self.prompt_manager = prompt_manager
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True
        self.multimodal_enabled = multimodal_enabled
        self.image_embeddings_client = image_embeddings_client
        self.global_blob_manager = global_blob_manager
        self.user_blob_manager = user_blob_manager

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

        documents: list[Document] = []
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
                        images=document.get("images"),
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
                knowledge_source_params=[
                    SearchIndexKnowledgeSourceParams(
                        knowledge_source_name=search_index_name,
                        filter_add_on=filter_add_on,
                    )
                ],
            )
        )

        # Map activity id -> agent's internal search query
        activities = response.activity
        activity_mapping: dict[int, str] = (
            {
                activity.id: activity.search_index_arguments.search
                for activity in activities
                if (
                    isinstance(activity, KnowledgeAgentSearchIndexActivityRecord)
                    and activity.search_index_arguments
                    and activity.search_index_arguments.search is not None
                )
            }
            if activities
            else {}
        )

        # No refs? we're done
        if not (response and response.references):
            return response, []

        # Extract references
        refs = [r for r in response.references if isinstance(r, KnowledgeAgentSearchIndexReference)]
        documents: list[Document] = []
        doc_to_ref_id: dict[str, str] = {}

        # Create documents from reference source data
        for ref in refs:
            if ref.source_data and ref.doc_key:
                # Note that ref.doc_key is the same as source_data["id"]
                documents.append(
                    Document(
                        id=ref.doc_key,
                        content=ref.source_data.get("content"),
                        category=ref.source_data.get("category"),
                        sourcepage=ref.source_data.get("sourcepage"),
                        sourcefile=ref.source_data.get("sourcefile"),
                        oids=ref.source_data.get("oids"),
                        groups=ref.source_data.get("groups"),
                        reranker_score=ref.reranker_score,
                        images=ref.source_data.get("images"),
                        search_agent_query=activity_mapping[ref.activity_source],
                    )
                )
                doc_to_ref_id[ref.doc_key] = ref.id
                if top and len(documents) >= top:
                    break

        if minimum_reranker_score is not None:
            documents = [doc for doc in documents if (doc.reranker_score or 0) >= minimum_reranker_score]

        if results_merge_strategy == "interleaved":
            documents = sorted(
                documents,
                key=lambda d: int(doc_to_ref_id.get(d.id, 0)) if d.id and doc_to_ref_id.get(d.id) else 0,
            )
        return response, documents

    async def get_sources_content(
        self,
        results: list[Document],
        use_semantic_captions: bool,
        include_text_sources: bool,
        download_image_sources: bool,
        user_oid: Optional[str] = None,
    ) -> DataPoints:
        """Extract text/image sources & citations from documents.

        Args:
            results: List of retrieved Document objects.
            use_semantic_captions: Whether to use semantic captions instead of full content text.
            download_image_sources: Whether to attempt downloading & base64 encoding referenced images.
            user_oid: Optional user object id for per-user storage access (ADLS scenarios).

        Returns:
            DataPoints: with text (list[str]), images (list[str - base64 data URI]), citations (list[str]).
        """

        def nonewlines(s: str) -> str:
            return s.replace("\n", " ").replace("\r", " ")

        citations = []
        text_sources = []
        image_sources = []
        seen_urls = set()

        for doc in results:
            # Get the citation for the source page
            citation = self.get_citation(doc.sourcepage)
            if citation not in citations:
                citations.append(citation)

            # If semantic captions are used, extract captions; otherwise, use content
            if include_text_sources:
                if use_semantic_captions and doc.captions:
                    text_sources.append(
                        f"{citation}: {nonewlines(' . '.join([cast(str, c.text) for c in doc.captions]))}"
                    )
                else:
                    text_sources.append(f"{citation}: {nonewlines(doc.content or '')}")

            if download_image_sources and hasattr(doc, "images") and doc.images:
                for img in doc.images:
                    # Skip if we've already processed this URL
                    if img["url"] in seen_urls or not img["url"]:
                        continue
                    seen_urls.add(img["url"])
                    url = await self.download_blob_as_base64(img["url"], user_oid=user_oid)
                    if url:
                        image_sources.append(url)
                    citations.append(self.get_image_citation(doc.sourcepage or "", img["url"]))
        return DataPoints(text=text_sources, images=image_sources, citations=citations)

    def get_citation(self, sourcepage: Optional[str]):
        return sourcepage or ""

    def get_image_citation(self, sourcepage: Optional[str], image_url: str):
        sourcepage_citation = self.get_citation(sourcepage)
        image_filename = image_url.split("/")[-1]
        return f"{sourcepage_citation}({image_filename})"

    async def download_blob_as_base64(self, blob_url: str, user_oid: Optional[str] = None) -> Optional[str]:
        """
        Downloads a blob from either Azure Blob Storage or Azure Data Lake Storage and returns it as a base64 encoded string.

        Args:
            blob_url: The URL or path to the blob to download
            user_oid: The user's object ID, required for Data Lake Storage operations and access control

        Returns:
            Optional[str]: The base64 encoded image data with data URI scheme prefix, or None if the blob cannot be downloaded
        """

        # Handle full URLs for both Blob Storage and Data Lake Storage
        if blob_url.startswith("http"):
            url_parts = blob_url.split("/")
            # Skip the domain parts and container/filesystem name to get the blob path
            # For blob: https://{account}.blob.core.windows.net/{container}/{blob_path}
            # For dfs: https://{account}.dfs.core.windows.net/{filesystem}/{path}
            blob_path = "/".join(url_parts[4:])
            # If %20 in URL, replace it with a space
            blob_path = blob_path.replace("%20", " ")
        else:
            # Treat as a direct blob path
            blob_path = blob_url

        # Download the blob using the appropriate client
        result = None
        if ".dfs.core.windows.net" in blob_url and self.user_blob_manager:
            result = await self.user_blob_manager.download_blob(blob_path, user_oid=user_oid)
        elif self.global_blob_manager:
            result = await self.global_blob_manager.download_blob(blob_path)

        if result:
            content, _ = result  # Unpack the tuple, ignoring properties
            img = base64.b64encode(content).decode("utf-8")
            return f"data:image/png;base64,{img}"
        return None

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

    async def compute_multimodal_embedding(self, q: str):
        if not self.image_embeddings_client:
            raise ValueError("Approach is missing an image embeddings client for multimodal queries")
        multimodal_query_vector = await self.image_embeddings_client.create_embedding_for_text(q)
        return VectorizedQuery(vector=multimodal_query_vector, k_nearest_neighbors=50, fields="images/embedding")

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
