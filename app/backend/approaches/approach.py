import base64
import json
import re
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import asdict, dataclass, field
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
    KnowledgeRetrievalLowReasoningEffort,
    KnowledgeRetrievalMediumReasoningEffort,
    KnowledgeRetrievalMinimalReasoningEffort,
    KnowledgeRetrievalSemanticIntent,
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
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from approaches.promptmanager import PromptManager
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager
from prepdocslib.embeddings import ImageEmbeddings


@dataclass
class ActivityDetail:
    id: int
    number: int
    type: str
    source: str
    query: str


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
    activity: Optional[ActivityDetail] = None
    images: Optional[list[dict[str, Any]]] = None

    def serialize_for_results(self) -> dict[str, Any]:
        result_dict = {
            "type": "searchIndex",
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
            "activity": asdict(self.activity) if self.activity else None,
            "images": self.images,
        }
        return result_dict


@dataclass
class WebResult:
    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    activity: Optional[ActivityDetail] = None

    def serialize_for_results(self) -> dict[str, Any]:
        return {
            "type": "web",
            "id": self.id,
            "ref_id": str(self.id),
            "title": self.title,
            "url": self.url,
            "activity": asdict(self.activity) if self.activity else None,
        }


@dataclass
class SharePointResult:
    id: Optional[str] = None
    web_url: Optional[str] = None
    content: Optional[str] = None
    title: Optional[str] = None
    reranker_score: Optional[float] = None
    activity: Optional[ActivityDetail] = None

    def serialize_for_results(self) -> dict[str, Any]:
        return {
            "type": "remoteSharePoint",
            "id": self.id,
            "ref_id": str(self.id),
            "web_url": self.web_url,
            "content": self.content,
            "title": self.title,
            "reranker_score": self.reranker_score,
            "activity": asdict(self.activity) if self.activity else None,
        }


@dataclass
class RewriteQueryResult:
    query: str
    messages: list[ChatCompletionMessageParam]
    completion: ChatCompletion
    reasoning_effort: ChatCompletionReasoningEffort


@dataclass
class ThoughtStep:
    title: str
    description: Optional[Any]
    props: Optional[dict[str, Any]] = None

    def update_token_usage(self, usage: CompletionUsage) -> None:
        if self.props:
            self.props["token_usage"] = TokenUsageProps.from_completion_usage(usage)


@dataclass
class AgenticRetrievalResults:
    """Results from agentic retrieval including activities, documents, web results, SharePoint results, and optional answer."""

    response: KnowledgeBaseRetrievalResponse
    documents: list[Document]
    web_results: list[WebResult]
    sharepoint_results: list[SharePointResult] = field(default_factory=list)
    answer: Optional[str] = None  # Synthesized answer when web knowledge source is used
    rewrite_result: Optional[RewriteQueryResult] = None
    activity_details_by_id: Optional[dict[int, ActivityDetail]] = None
    thoughts: list[ThoughtStep] = field(default_factory=list)


@dataclass
class DataPoints:
    text: Optional[list[str]] = None
    images: Optional[list] = None
    citations: Optional[list[str]] = None
    external_results_metadata: Optional[list[dict[str, Any]]] = None
    citation_activity_details: Optional[dict[str, dict[str, Any]]] = None


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


class Approach:
    """
    RAG approach for multi-turn chat that retrieves relevant documents and generates responses.

    Supports two retrieval modes:
    - Search API: Uses Azure AI Search directly with optional query rewriting, vector search, and semantic ranking.
    - Agentic retrieval: Uses Azure AI Search knowledge base retrieval with optional web and SharePoint sources.

    The approach rewrites the user's question into a search query, retrieves relevant documents,
    and sends the conversation history with search results to OpenAI to generate a response.
    """

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
        *,
        search_client: SearchClient,
        search_index_name: Optional[str],
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
        self.query_rewrite_prompt = self.prompt_manager.load_prompt("chat_query_rewrite.prompty")
        self.query_rewrite_tools = self.prompt_manager.load_tools("chat_query_rewrite_tools.json")
        self.answer_prompt = self.prompt_manager.load_prompt("chat_answer_question.prompty")
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
        no_response_token: Optional[str] = None,
    ) -> RewriteQueryResult:
        query_messages = self.prompt_manager.render_prompt(prompt_template, prompt_variables)
        rewrite_reasoning_effort = self.get_lowest_reasoning_effort(self.chatgpt_model)

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
                reasoning_effort=rewrite_reasoning_effort,
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
            reasoning_effort=rewrite_reasoning_effort,
        )

    async def run_agentic_retrieval(
        self,
        messages: list[ChatCompletionMessageParam],
        knowledgebase_client: KnowledgeBaseRetrievalClient,
        search_index_name: str,
        filter_add_on: Optional[str] = None,
        minimum_reranker_score: Optional[float] = None,
        access_token: Optional[str] = None,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False,
        retrieval_reasoning_effort: Optional[str] = None,
        should_rewrite_query: bool = True,
    ) -> AgenticRetrievalResults:
        # STEP 1: Invoke agentic retrieval
        thoughts = []

        knowledge_source_params = [
            SearchIndexKnowledgeSourceParams(
                knowledge_source_name=search_index_name,
                filter_add_on=filter_add_on,
                include_references=True,
                include_reference_source_data=True,
                always_query_source=False,
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
                    always_query_source=False,
                )
            )

        if use_sharepoint_source:
            knowledge_source_params_list.append(
                RemoteSharePointKnowledgeSourceParams(
                    knowledge_source_name="sharepoint",
                    include_references=True,
                    include_reference_source_data=True,
                    always_query_source=False,
                )
            )

        agentic_retrieval_input: dict[str, Any] = {}
        rewrite_result = None
        if retrieval_reasoning_effort == "minimal" and should_rewrite_query:
            original_user_query = messages[-1]["content"]
            if not isinstance(original_user_query, str):
                raise ValueError("The most recent message content must be a string.")

            rewrite_result = await self.rewrite_query(
                prompt_template=self.query_rewrite_prompt,
                prompt_variables={"user_query": original_user_query, "past_messages": messages[:-1]},
                overrides={},
                chatgpt_model=self.chatgpt_model,
                chatgpt_deployment=self.chatgpt_deployment,
                user_query=original_user_query,
                response_token_limit=self.get_response_token_limit(
                    self.chatgpt_model, 100
                ),  # Setting too low risks malformed JSON, setting too high may affect performance
                tools=self.query_rewrite_tools,
                temperature=0.0,  # Minimize creativity for search query generation
                no_response_token=self.QUERY_REWRITE_NO_RESPONSE,
            )
            thoughts.append(
                self.format_thought_step_for_chatcompletion(
                    title="Prompt to generate search query",
                    messages=rewrite_result.messages,
                    overrides={},
                    model=self.chatgpt_model,
                    deployment=self.chatgpt_deployment,
                    usage=rewrite_result.completion.usage,
                    reasoning_effort=rewrite_result.reasoning_effort,
                )
            )
            agentic_retrieval_input["intents"] = [KnowledgeRetrievalSemanticIntent(search=rewrite_result.query)]
        elif retrieval_reasoning_effort == "minimal":
            last_content = messages[-1]["content"]
            if not isinstance(last_content, str):
                raise ValueError("The most recent message content must be a string.")
            agentic_retrieval_input["intents"] = [KnowledgeRetrievalSemanticIntent(search=last_content)]
        else:
            kb_messages: list[KnowledgeBaseMessage] = [
                KnowledgeBaseMessage(
                    role=str(msg["role"]), content=[KnowledgeBaseMessageTextContent(text=str(msg["content"]))]
                )
                for msg in messages
                if msg["role"] != "system"
            ]
            agentic_retrieval_input["messages"] = kb_messages
        # When we're not using a web source, set output mode to extractiveData to avoid synthesized answer
        if not use_web_source:
            agentic_retrieval_input["output_mode"] = "extractiveData"

        retrieval_effort: Optional[
            KnowledgeRetrievalMinimalReasoningEffort
            | KnowledgeRetrievalLowReasoningEffort
            | KnowledgeRetrievalMediumReasoningEffort
        ] = None
        if retrieval_reasoning_effort == "minimal":
            retrieval_effort = KnowledgeRetrievalMinimalReasoningEffort()
        elif retrieval_reasoning_effort == "low":
            retrieval_effort = KnowledgeRetrievalLowReasoningEffort()
        elif retrieval_reasoning_effort == "medium":
            retrieval_effort = KnowledgeRetrievalMediumReasoningEffort()

        request_kwargs: dict[str, Any] = {
            "knowledge_source_params": knowledge_source_params_list,
            "include_activity": True,
            "retrieval_reasoning_effort": retrieval_effort,
        }
        request_kwargs.update(agentic_retrieval_input)

        response = await knowledgebase_client.retrieve(
            retrieval_request=KnowledgeBaseRetrievalRequest(**request_kwargs),
            x_ms_query_source_authorization=access_token,
        )

        # Map activity id -> agent's internal search query and citation
        activities = response.activity or []
        activity_details_by_id: dict[int, ActivityDetail] = {}

        for index, activity in enumerate(activities):
            search_query = None
            if isinstance(activity, KnowledgeBaseSearchIndexActivityRecord):
                if activity.search_index_arguments:
                    search_query = activity.search_index_arguments.search
            elif isinstance(activity, KnowledgeBaseWebActivityRecord):
                if activity.web_arguments:
                    search_query = activity.web_arguments.search
            elif isinstance(activity, KnowledgeBaseRemoteSharePointActivityRecord):
                if activity.remote_share_point_arguments:
                    search_query = activity.remote_share_point_arguments.search

            activity_details_by_id[activity.id] = ActivityDetail(
                id=activity.id,
                number=index + 1,
                type=activity.type or "",
                source=getattr(activity, "knowledge_source_name", "")
                or "",  # Not all activity types have knowledge_source_name
                query=search_query or "",
            )

        # Extract references
        references = response.references or []

        document_refs = [
            r for r in references if isinstance(r, KnowledgeBaseSearchIndexReference) or hasattr(r, "doc_key")
        ]
        document_results: list[Document] = []
        # Create documents from reference source data
        for ref in document_refs:
            if ref.source_data and ref.doc_key:
                # Note that ref.doc_key is the same as source_data["id"]
                document_results.append(
                    Document(
                        id=ref.doc_key,
                        ref_id=ref.id,
                        content=ref.source_data.get("content"),
                        category=ref.source_data.get("category"),
                        sourcepage=ref.source_data.get("sourcepage"),
                        sourcefile=ref.source_data.get("sourcefile"),
                        oids=ref.source_data.get("oids"),
                        groups=ref.source_data.get("groups"),
                        reranker_score=getattr(ref, "reranker_score", None),
                        images=ref.source_data.get("images"),
                        activity=activity_details_by_id[ref.activity_source],
                    )
                )

        # We need to handle KnowledgeBaseWebReference separately if web knowledge source is used
        web_refs = [r for r in references if isinstance(r, KnowledgeBaseWebReference)]
        web_results: list[WebResult] = []
        for ref in web_refs:
            web_result = WebResult(
                id=ref.id, title=ref.title, url=ref.url, activity=activity_details_by_id[ref.activity_source]
            )
            web_results.append(web_result)

        # Handle KnowledgeBaseRemoteSharePointReference if SharePoint knowledge source is used
        sharepoint_refs = [r for r in references if isinstance(r, KnowledgeBaseRemoteSharePointReference)]
        sharepoint_results: list[SharePointResult] = []
        for ref in sharepoint_refs:
            # Extract content from all sourceData.extracts[].text and concatenate
            content = None
            if ref.source_data and "extracts" in ref.source_data and len(ref.source_data["extracts"]) > 0:
                extracts = [extract.get("text", "") for extract in ref.source_data["extracts"]]
                content = "\n\n".join(extracts) if extracts else None

            # Extract title from sourceData.resourceMetadata.title
            title = None
            if ref.source_data and "resourceMetadata" in ref.source_data:
                title = ref.source_data["resourceMetadata"].get("title")

            sharepoint_result = SharePointResult(
                id=ref.id,
                web_url=ref.web_url,
                content=content,
                title=title,
                reranker_score=getattr(ref, "reranker_score", None),
                activity=activity_details_by_id[ref.activity_source],
            )
            sharepoint_results.append(sharepoint_result)

        # Extract answer from response if web knowledge source provided one
        answer: Optional[str] = None
        if (
            use_web_source
            and response.response
            and len(response.response) > 0
            and len(response.response[0].content) > 0
        ):
            message_content = response.response[0].content[0]
            if isinstance(message_content, KnowledgeBaseMessageTextContent):
                raw_answer: Optional[str] = message_content.text
                # Replace all ref_id tokens (web -> URL, documents -> sourcepage, SharePoint -> web_url)
                if raw_answer:
                    answer = self.replace_all_ref_ids(raw_answer, document_results, web_results, sharepoint_results)

        thoughts.append(
            ThoughtStep(
                "Agentic retrieval response",
                [result.serialize_for_results() for result in document_results + web_results + sharepoint_results],
                {
                    "query_plan": (
                        [activity.as_dict() for activity in response.activity] if response.activity else None
                    ),
                    "model": self.knowledgebase_model,
                    "deployment": self.knowledgebase_deployment,
                    "reranker_threshold": minimum_reranker_score,
                    "filter": filter_add_on,
                },
            )
        )

        return AgenticRetrievalResults(
            response=response,
            documents=document_results,
            web_results=web_results,
            sharepoint_results=sharepoint_results,
            answer=answer,
            rewrite_result=rewrite_result,
            activity_details_by_id=activity_details_by_id,
            thoughts=thoughts,
        )

    def replace_all_ref_ids(
        self,
        answer: str,
        documents: list[Document],
        web_results: list[WebResult],
        sharepoint_results: Optional[list[SharePointResult]] = None,
    ) -> str:
        """Replace [ref_id:<id>] tokens with document sourcepage, web URL, or SharePoint web_url.

        Priority: web result -> SharePoint result -> document.
        Unknown ids left untouched.
        """
        doc_map = {d.ref_id: d.sourcepage for d in documents if d.ref_id and d.sourcepage}
        web_map = {str(w.id): w.url for w in web_results if w.id and w.url}
        sharepoint_entries = sharepoint_results or []
        sharepoint_map = {str(sp.id): sp.web_url.split("/")[-1] for sp in sharepoint_entries if sp.id and sp.web_url}

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
        external_results_metadata: list[dict[str, Any]] = []
        citation_activity_details: dict[str, dict[str, Any]] = {}

        for doc in results:
            # Get the citation for the source page
            citation = self.get_citation(doc.sourcepage)
            if citation not in citations:
                citations.append(citation)
                # Add activity details if available
                if doc.activity:
                    citation_activity_details[citation] = asdict(doc.activity)

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
                    image_citation = self.get_image_citation(doc.sourcepage or "", img["url"])
                    citations.append(image_citation)
        if web_results:
            for web in web_results:
                citation = self.get_citation(web.url)
                if citation and citation not in citations:
                    citations.append(citation)
                    # Add activity details if available
                    if web.activity:
                        citation_activity_details[citation] = asdict(web.activity)
                external_results_metadata.append(
                    {
                        "id": web.id,
                        "title": web.title,
                        "url": web.url,
                        "activity": asdict(web.activity) if web.activity else None,
                    }
                )
        if sharepoint_results:
            for sp in sharepoint_results:
                # Extract filename from web_url for citation
                filename = sp.web_url.split("/")[-1] if sp.web_url else ""
                citation = self.get_citation(filename)
                if citation and citation not in citations:
                    citations.append(citation)
                    # Add activity details if available
                    if sp.activity:
                        citation_activity_details[citation] = asdict(sp.activity)
                if include_text_sources and sp.content:
                    text_sources.append(f"{citation}: {clean_source(sp.content)}")
                external_results_metadata.append(
                    {
                        "id": sp.id,
                        "title": sp.title or "",
                        "url": sp.web_url or "",
                        "snippet": clean_source(sp.content or ""),
                        "activity": asdict(sp.activity) if sp.activity else None,
                    }
                )

        return DataPoints(
            text=text_sources,
            images=image_sources,
            citations=citations,
            external_results_metadata=external_results_metadata,
            citation_activity_details=citation_activity_details if citation_activity_details else None,
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
        container: Optional[str] = None
        if blob_url.startswith("http"):
            url_parts = blob_url.split("/")
            # Extract container name from URL
            # For blob: https://{account}.blob.core.windows.net/{container}/{blob_path}
            # For dfs: https://{account}.dfs.core.windows.net/{filesystem}/{path}
            container = url_parts[3]
            # Extract the blob path portion (everything after the container/filesystem segment)
            blob_path = "/".join(url_parts[4:])
            # If %20 in URL, replace it with a space
            blob_path = blob_path.replace("%20", " ")
        else:
            # Treat as a direct blob path
            blob_path = blob_url

        # Download the blob using the appropriate client
        result = None
        if ".dfs.core.windows.net" in blob_url and self.user_blob_manager:
            result = await self.user_blob_manager.download_blob(blob_path, user_oid=user_oid, container=container)
        elif self.global_blob_manager:
            result = await self.global_blob_manager.download_blob(blob_path, container=container)

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

    def extract_followup_questions(self, content: Optional[str]):
        if content is None:
            return content, []
        return content.split("<<")[0], re.findall(r"<<([^>>]+)>>", content)

    def get_search_query(self, chat_completion: ChatCompletion, default_query: str) -> str:
        """Read the optimized search query from a chat completion tool call."""
        try:
            return self.extract_rewritten_query(
                chat_completion, default_query, no_response_token=self.QUERY_REWRITE_NO_RESPONSE
            )
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
            prompt_template=self.query_rewrite_prompt,
            prompt_variables={"user_query": original_user_query, "past_messages": messages[:-1]},
            overrides=overrides,
            chatgpt_model=self.chatgpt_model,
            chatgpt_deployment=self.chatgpt_deployment,
            user_query=original_user_query,
            response_token_limit=self.get_response_token_limit(
                self.chatgpt_model, 100
            ),  # Setting too low risks malformed JSON, setting too high may affect performance
            tools=self.query_rewrite_tools,
            temperature=0.0,  # Minimize creativity for search query generation
            no_response_token=self.QUERY_REWRITE_NO_RESPONSE,
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

        if not self.search_index_name:
            raise ValueError("Agentic retrieval requested but search_index_name is not configured")

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
