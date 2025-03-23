from typing import Any, Awaitable, Callable, Optional

from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import ContainerClient
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
)
from openai_messages_token_helper import get_token_limit

from approaches.approach import Approach, ThoughtStep
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper
from core.imageshelper import fetch_image


class RetrieveThenReadVisionApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the AI Search and OpenAI APIs directly. It first retrieves
    top documents including images from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    def __init__(
        self,
        *,
        search_client: SearchClient,
        blob_container_client: ContainerClient,
        openai_client: AsyncOpenAI,
        auth_helper: AuthenticationHelper,
        gpt4v_deployment: Optional[str],
        gpt4v_model: str,
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        embedding_dimensions: int,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        vision_endpoint: str,
        vision_token_provider: Callable[[], Awaitable[str]],
        prompt_manager: PromptManager,
    ):
        self.search_client = search_client
        self.blob_container_client = blob_container_client
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.embedding_model = embedding_model
        self.embedding_deployment = embedding_deployment
        self.embedding_dimensions = embedding_dimensions
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.gpt4v_deployment = gpt4v_deployment
        self.gpt4v_model = gpt4v_model
        self.query_language = query_language
        self.query_speller = query_speller
        self.vision_endpoint = vision_endpoint
        self.vision_token_provider = vision_token_provider
        self.gpt4v_token_limit = get_token_limit(gpt4v_model, self.ALLOW_NON_GPT_MODELS)
        self.prompt_manager = prompt_manager
        self.answer_prompt = self.prompt_manager.load_prompt("ask_answer_question_vision.prompty")

    async def run(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> dict[str, Any]:
        q = messages[-1]["content"]
        if not isinstance(q, str):
            raise ValueError("The most recent message content must be a string.")

        overrides = context.get("overrides", {})
        seed = overrides.get("seed", None)
        auth_claims = context.get("auth_claims", {})
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_query_rewriting = True if overrides.get("query_rewriting") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        filter = self.build_filter(overrides, auth_claims)

        vector_fields = overrides.get("vector_fields", ["embedding"])
        send_text_to_gptvision = overrides.get("gpt4v_input") in ["textAndImages", "texts", None]
        send_images_to_gptvision = overrides.get("gpt4v_input") in ["textAndImages", "images", None]

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors = []
        if use_vector_search:
            for field in vector_fields:
                vector = (
                    await self.compute_text_embedding(q)
                    if field == "embedding"
                    else await self.compute_image_embedding(q)
                )
                vectors.append(vector)

        results = await self.search(
            top,
            q,
            filter,
            vectors,
            use_text_search,
            use_vector_search,
            use_semantic_ranker,
            use_semantic_captions,
            minimum_search_score,
            minimum_reranker_score,
            use_query_rewriting,
        )

        # Process results
        text_sources = []
        image_sources = []
        if send_text_to_gptvision:
            text_sources = self.get_sources_content(results, use_semantic_captions, use_image_citation=True)
        if send_images_to_gptvision:
            for result in results:
                url = await fetch_image(self.blob_container_client, result)
                if url:
                    image_sources.append(url)

        rendered_answer_prompt = self.prompt_manager.render_prompt(
            self.answer_prompt,
            self.get_system_prompt_variables(overrides.get("prompt_template"))
            | {"user_query": q, "text_sources": text_sources, "image_sources": image_sources},
        )

        chat_completion = await self.openai_client.chat.completions.create(
            model=self.gpt4v_deployment if self.gpt4v_deployment else self.gpt4v_model,
            messages=rendered_answer_prompt.all_messages,
            temperature=overrides.get("temperature", 0.3),
            max_tokens=1024,
            n=1,
            seed=seed,
        )

        extra_info = {
            "data_points": {"text": text_sources, "images": image_sources},
            "thoughts": [
                ThoughtStep(
                    "Search using user query",
                    q,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "use_query_rewriting": use_query_rewriting,
                        "top": top,
                        "filter": filter,
                        "vector_fields": vector_fields,
                        "use_vector_search": use_vector_search,
                        "use_text_search": use_text_search,
                    },
                ),
                ThoughtStep(
                    "Search results",
                    [result.serialize_for_results() for result in results],
                ),
                ThoughtStep(
                    "Prompt to generate answer",
                    rendered_answer_prompt.all_messages,
                    (
                        {"model": self.gpt4v_model, "deployment": self.gpt4v_deployment}
                        if self.gpt4v_deployment
                        else {"model": self.gpt4v_model}
                    ),
                ),
            ],
        }

        return {
            "message": {
                "content": chat_completion.choices[0].message.content,
                "role": chat_completion.choices[0].message.role,
            },
            "context": extra_info,
            "session_state": session_state,
        }
