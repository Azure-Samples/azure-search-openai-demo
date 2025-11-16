import base64
import json
import re
from abc import ABC
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict, cast

from azure.search.documents.aio import SearchClient
from azure.search.documents.knowledgebases.aio import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRemoteSharePointActivityRecord,
    KnowledgeBaseRemoteSharePointReference,
    KnowledgeBaseRetrievalRequest,
    KnowledgeBaseRetrievalResponse,
    KnowledgeBaseSearchIndexActivityRecord,
    KnowledgeBaseSearchIndexReference,
    KnowledgeBaseWebActivityRecord,
    KnowledgeBaseWebReference,
    KnowledgeSourceParams,
    RemoteSharePointKnowledgeSourceParams,
    SearchIndexKnowledgeSourceParams,
    WebKnowledgeSourceParams,
)
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
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager
from prepdocslib.embeddings import ImageEmbeddings


@dataclass
class Document:
    id: Optional[str] = None
    ref_id: Optional[str] = None  # Reference id from agentic retrieval (if applicable)
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
class WebResult:
    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    search_agent_query: Optional[str] = None

    def serialize_for_results(self) -> dict[str, Any]:
        return {
            "type": "web",
            "id": self.id,
            "ref_id": str(self.id),
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "search_agent_query": self.search_agent_query,
        }


@dataclass
class SharePointResult:
    id: Optional[str] = None
    web_url: Optional[str] = None
    content: Optional[str] = None
    title: Optional[str] = None
    reranker_score: Optional[float] = None
    search_agent_query: Optional[str] = None

    def serialize_for_results(self) -> dict[str, Any]:
        return {
            "type": "sharepoint",
            "id": self.id,
            "ref_id": str(self.id),
            "web_url": self.web_url,
            "content": self.content,
            "title": self.title,
            "reranker_score": self.reranker_score,
            "search_agent_query": self.search_agent_query,
        }


@dataclass
class AgenticRetrievalResults:
    """Results from agentic retrieval including activities, documents, web results, SharePoint results, and optional answer."""

    response: KnowledgeBaseRetrievalResponse
    documents: list[Document]
    web_results: list[WebResult]
    sharepoint_results: list[SharePointResult] = field(default_factory=list)
    answer: Optional[str] = None  # Synthesized answer when web knowledge source is used

    def get_ordered_results(self) -> list[dict[str, Any]]:
        """Get all results (documents, web, and SharePoint) in their original reference order."""
        # Combine all results with their ref_ids
        all_results: list[tuple[str, dict[str, Any]]] = []
        
        for doc in self.documents:
            if doc.ref_id:
                all_results.append((doc.ref_id, doc.serialize_for_results()))
        
        for web in self.web_results:
            if web.id:
                all_results.append((str(web.id), web.serialize_for_results()))
        
        for sp in self.sharepoint_results:
            if sp.id:
                all_results.append((str(sp.id), sp.serialize_for_results()))
        
        # Sort by ref_id (numeric order)
        all_results.sort(key=lambda x: int(x[0]) if x[0].isdigit() else float('inf'))
        
        return [result for _, result in all_results]


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
    web: Optional[list[dict[str, Any]]] = None


@dataclass
class ExtraInfo:
    data_points: DataPoints
    thoughts: list[ThoughtStep] = field(default_factory=list)
    followup_questions: Optional[list[Any]] = None
    answer: Optional[str] = None  # Only when web knowledge source is used


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


@dataclass
class RewriteQueryResult:
    query: str
    messages: list[ChatCompletionMessageParam]
    completion: ChatCompletion


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
    QUERY_REWRITE_NO_RESPONSE = "0"

    def __init__(
        self,
        search_client: SearchClient,
        openai_client: AsyncOpenAI,
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

    def build_filter(self, overrides: dict[str, Any]) -> Optional[str]:
        include_category = overrides.get("include_category")
        exclude_category = overrides.get("exclude_category")
        filters = []
        if include_category:
            filters.append("category eq '{}'".format(include_category.replace("'", "''")))
        if exclude_category:
            filters.append("category ne '{}'".format(exclude_category.replace("'", "''")))
        return None if not filters else " and ".join(filters)

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
        access_token: Optional[str] = None,
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
                x_ms_query_source_authorization=access_token,
            )
        else:
            results = await self.search_client.search(
                search_text=search_text,
                filter=filter,
                top=top,
                vector_queries=search_vectors,
                x_ms_query_source_authorization=access_token,
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

    def extract_rewritten_query(
        self,
        chat_completion: ChatCompletion,
        user_query: str,
        no_response_token: Optional[str] = None,
    ) -> str:
        response_message = chat_completion.choices[0].message

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                if tool_call.type != "function":
                    continue
                arguments_payload = tool_call.function.arguments or "{}"
                try:
                    parsed_arguments = json.loads(arguments_payload)
                except json.JSONDecodeError:
                    continue
                search_query = parsed_arguments.get("search_query")
                if search_query and (no_response_token is None or search_query != no_response_token):
                    return search_query

        if response_message.content:
            candidate = response_message.content.strip()
            if candidate and (no_response_token is None or candidate != no_response_token):
                return candidate

        return user_query

    async def rewrite_query(
        self,
        *,
        prompt_template: Any,
        prompt_variables: dict[str, Any],
        overrides: dict[str, Any],
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],
        user_query: str,
        response_token_limit: int,
        tools: Optional[list[ChatCompletionToolParam]] = None,
        temperature: float = 0.0,
        reasoning_effort: Optional[ChatCompletionReasoningEffort] = None,
        no_response_token: Optional[str] = None,
    ) -> RewriteQueryResult:
        query_messages = self.prompt_manager.render_prompt(prompt_template, prompt_variables)

        chat_completion = cast(
            ChatCompletion,
            await self.create_chat_completion(
                chatgpt_deployment,
                chatgpt_model,
                messages=query_messages,
                overrides=overrides,
                response_token_limit=response_token_limit,
                temperature=temperature,
                tools=tools,
                reasoning_effort=reasoning_effort,
            ),
        )

        rewritten_query = self.extract_rewritten_query(
            chat_completion,
            user_query,
            no_response_token=no_response_token,
        )

        return RewriteQueryResult(
            query=rewritten_query,
            messages=query_messages,
            completion=chat_completion,
        )

    async def run_agentic_retrieval(
        self,
        messages: list[ChatCompletionMessageParam],
        agent_client: KnowledgeBaseRetrievalClient,
        search_index_name: str,
        top: Optional[int] = None,
        filter_add_on: Optional[str] = None,
        minimum_reranker_score: Optional[float] = None,
        results_merge_strategy: Optional[str] = None,
        access_token: Optional[str] = None,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False
    ) -> AgenticRetrievalResults:
        # STEP 1: Invoke agentic retrieval

        knowledge_source_params = [
            SearchIndexKnowledgeSourceParams(
                knowledge_source_name=search_index_name,
                filter_add_on=filter_add_on,
                include_references=True,
                include_reference_source_data=True,
                always_query_source=True,
                reranker_threshold=minimum_reranker_score,
            )
        ]
        # Build list as KnowledgeSourceParams for type variance
        knowledge_source_params_list: list[KnowledgeSourceParams] = cast(
            list[KnowledgeSourceParams], knowledge_source_params
        )

        if use_web_source:
            knowledge_source_params_list.append(
                WebKnowledgeSourceParams(
                    knowledge_source_name="web",
                    include_references=True,
                    include_reference_source_data=True,
                )
            )

        if use_sharepoint_source:
            print("Including SharePoint knowledge source in agentic retrieval")
            print("Access token", access_token)
            knowledge_source_params_list.append(
                RemoteSharePointKnowledgeSourceParams(
                    knowledge_source_name="sharepoint",
                    include_references=True,
                    include_reference_source_data=True,
                    always_query_source=True
                )
            )

        # if minimal: pass intents 
        #request_params = {}
        #if self.reasoning_effort == "minimal":
        #    request_params["intents"] = []
        """
        intents=[
            KnowledgeRetrievalSemanticIntent(
                search="What is the responsibility of the Zava CEO?"
            ),
            KnowledgeRetrievalSemanticIntent(
                search="What Zava health plan would you recommend if they wanted the best coverage for mental health services?"
            )
        ],
        """
        response = await agent_client.retrieve(
            retrieval_request=KnowledgeBaseRetrievalRequest(

                messages=[
                    KnowledgeBaseMessage(
                        role=str(msg["role"]), content=[KnowledgeBaseMessageTextContent(text=str(msg["content"]))]
                    )
                    for msg in messages
                    if msg["role"] != "system"
                ],
                knowledge_source_params=knowledge_source_params_list,
                include_activity=True,
            ),
            # TODO: retrieval_reasoning_effort=KnowledgeRetrievalMinimalReasoningEffort(),
            # TODO: Only pass access token if knowledge source requires it?
            x_ms_query_source_authorization=access_token,
        )

        # Map activity id -> agent's internal search query
        activities = response.activity or []
        activity_mapping: dict[Any, Optional[str]] = {}

        for activity in activities:
            print("Processing activity:", activity)
            if isinstance(activity, KnowledgeBaseSearchIndexActivityRecord):
                if activity.search_index_arguments:
                    activity_mapping[activity.id] = activity.search_index_arguments.search
            elif isinstance(activity, KnowledgeBaseWebActivityRecord):
                if activity.web_arguments:
                    activity_mapping[activity.id] = activity.web_arguments.search
            elif isinstance(activity, KnowledgeBaseRemoteSharePointActivityRecord):
                if activity.remote_share_point_arguments:
                    activity_mapping[activity.id] = activity.remote_share_point_arguments.search

        # No refs? we're done
        if not (response and response.references):
            return AgenticRetrievalResults(
                response=response, documents=[], web_results=[], sharepoint_results=[]
            )

        # Extract references
        ref_order: dict[str, int] = {}
        for index, ref in enumerate(response.references):
            ref_id = getattr(ref, "id", None)
            if ref_id is not None:
                ref_order[str(ref_id)] = index

        refs = [r for r in response.references if isinstance(r, KnowledgeBaseSearchIndexReference) or hasattr(r, "doc_key")]
        documents: list[Document] = []
        doc_to_ref_id: dict[str, int] = {}
        # Create documents from reference source data
        for ref in refs:
            if ref.source_data and ref.doc_key:
                # Note that ref.doc_key is the same as source_data["id"]
                documents.append(
                    Document(
                        id=ref.doc_key,
                        ref_id=str(getattr(ref, "id", "")),
                        content=ref.source_data.get("content"),
                        category=ref.source_data.get("category"),
                        sourcepage=ref.source_data.get("sourcepage"),
                        sourcefile=ref.source_data.get("sourcefile"),
                        oids=ref.source_data.get("oids"),
                        groups=ref.source_data.get("groups"),
                        reranker_score=getattr(ref, "reranker_score", None),
                        images=ref.source_data.get("images"),
                        search_agent_query=activity_mapping[ref.activity_source],
                    )
                )
                doc_to_ref_id[ref.doc_key] = int(ref.id)
                if top and len(documents) >= top:
                    break
        # We need to handle KnowledgeBaseWebReference separately if web knowledge source is used
        web_refs = [r for r in response.references if isinstance(r, KnowledgeBaseWebReference)]
        web_results: list[WebResult] = []
        for ref in web_refs:
            web_result = WebResult(
                id=ref.id,
                title=ref.title,
                url=ref.url,
                search_agent_query=activity_mapping[ref.activity_source],
            )
            web_results.append(web_result)

        # Handle KnowledgeBaseRemoteSharePointReference if SharePoint knowledge source is used
        sharepoint_refs = [r for r in response.references if isinstance(r, KnowledgeBaseRemoteSharePointReference)]
        sharepoint_results: list[SharePointResult] = []
        for ref in sharepoint_refs:
            sharepoint_result = SharePointResult(
                id=ref.id,
                web_url=ref.web_url,
                content=ref.source_data.get("content") if ref.source_data else None,
                title=ref.source_data.get("title") if ref.source_data else None,
                reranker_score=getattr(ref, "reranker_score", None),
                search_agent_query=activity_mapping[ref.activity_source],
            )
            sharepoint_results.append(sharepoint_result)

        if results_merge_strategy == "interleaved":
            documents = sorted(
                documents,
                key=lambda d: int(doc_to_ref_id.get(d.id, 0)) if d.id and doc_to_ref_id.get(d.id) else 0,
            )

        # Extract answer from response if web knowledge source provided one
        answer = None
        if response.response and len(response.response) > 0 and len(response.response[0].content) > 0:
            content = response.response[0].content[0]
            if isinstance(content, KnowledgeBaseMessageTextContent):
                raw_answer = content.text
                # Replace all ref_id tokens (web -> URL, documents -> sourcepage, SharePoint -> web_url)
                answer = self.replace_all_ref_ids(raw_answer, documents, web_results, sharepoint_results)

        return AgenticRetrievalResults(
            response=response,
            documents=documents,
            web_results=web_results,
            sharepoint_results=sharepoint_results,
            answer=answer,
        )

    def replace_all_ref_ids(
        self,
        answer: str,
        documents: list[Document],
        web_results: list[WebResult],
        sharepoint_results: list[SharePointResult],
    ) -> str:
        """Replace [ref_id:<id>] tokens with document sourcepage, web URL, or SharePoint web_url.

        Priority: web result -> SharePoint result -> document.
        Unknown ids left untouched.
        """
        doc_map = {d.ref_id: d.sourcepage for d in documents if d.ref_id and d.sourcepage}
        web_map = {str(w.id): w.url for w in web_results if w.id and w.url}
        sharepoint_map = {str(sp.id): sp.web_url for sp in sharepoint_results if sp.id and sp.web_url}

        def _sub(match: re.Match) -> str:
            ref_id = match.group(1)
            if ref_id in web_map and web_map[ref_id]:
                return f"[{web_map[ref_id]}]"
            if ref_id in sharepoint_map and sharepoint_map[ref_id]:
                return f"[{sharepoint_map[ref_id]}]"
            if ref_id in doc_map and doc_map[ref_id]:
                return f"[{doc_map[ref_id]}]"
            return match.group(0)

        return re.sub(r"\[ref_id:([^\]]+)\]", _sub, answer)

    async def get_sources_content(
        self,
        results: list[Document],
        use_semantic_captions: bool,
        include_text_sources: bool,
        download_image_sources: bool,
        user_oid: Optional[str] = None,
        web_results: Optional[list[WebResult]] = None,
        sharepoint_results: Optional[list[SharePointResult]] = None,
    ) -> DataPoints:
        """Extract text/image sources & citations from documents.

        Args:
            results: List of retrieved Document objects.
            use_semantic_captions: Whether to use semantic captions instead of full content text.
            download_image_sources: Whether to attempt downloading & base64 encoding referenced images.
            user_oid: Optional user object id for per-user storage access (ADLS scenarios).
            web_results: Optional list of web retrieval results to expose to clients.
            sharepoint_results: Optional list of SharePoint retrieval results to expose to clients.

        Returns:
            DataPoints: with text (list[str]), images (list[str - base64 data URI]), citations (list[str]).
        """

        def clean_source(s: str) -> str:
            s = s.replace("\n", " ").replace("\r", " ")  # normalize newlines to spaces
            s = s.replace(":::", "&#58;&#58;&#58;")  # escape DocFX/markdown triple colons
            return s

        citations = []
        text_sources = []
        image_sources = []
        seen_urls = set()
        web_sources: list[dict[str, Any]] = []

        for doc in results:
            # Get the citation for the source page
            citation = self.get_citation(doc.sourcepage)
            if citation not in citations:
                citations.append(citation)

            # If semantic captions are used, extract captions; otherwise, use content
            if include_text_sources:
                if use_semantic_captions and doc.captions:
                    cleaned = clean_source(" . ".join([cast(str, c.text) for c in doc.captions]))
                else:
                    cleaned = clean_source(doc.content or "")
                text_sources.append(f"{citation}: {cleaned}")

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
        if web_results:
            for web in web_results:
                citation = self.get_citation(web.url)
                if citation and citation not in citations:
                    citations.append(citation)
                web_sources.append(
                    {
                        "id": web.id,
                        "title": web.title,
                        "url": web.url,
                        "snippet": clean_source(web.snippet or ""),
                        "search_agent_query": web.search_agent_query,
                    }
                )
        if sharepoint_results:
            for sp in sharepoint_results:
                citation = self.get_citation(sp.web_url)
                if citation and citation not in citations:
                    citations.append(citation)
                if include_text_sources and sp.content:
                    text_sources.append(f"{citation}: {clean_source(sp.content)}")
                web_sources.append(
                    {
                        "id": sp.id,
                        "title": sp.title or "",
                        "url": sp.web_url or "",
                        "snippet": clean_source(sp.content or ""),
                        "search_agent_query": sp.search_agent_query,
                    }
                )
        return DataPoints(
            text=text_sources,
            images=image_sources,
            citations=citations,
            web=web_sources,
        )

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
        return VectorizedQuery(vector=query_vector, k=50, fields=self.embedding_field)

    async def compute_multimodal_embedding(self, q: str):
        if not self.image_embeddings_client:
            raise ValueError("Approach is missing an image embeddings client for multimodal queries")
        multimodal_query_vector = await self.image_embeddings_client.create_embedding_for_text(q)
        return VectorizedQuery(vector=multimodal_query_vector, k=50, fields="images/embedding")

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
    ) -> Awaitable[ChatCompletion] | Awaitable[AsyncStream[ChatCompletionChunk]]:
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
