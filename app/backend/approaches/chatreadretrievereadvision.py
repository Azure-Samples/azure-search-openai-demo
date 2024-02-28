from typing import Any, Awaitable, Callable, Coroutine, Optional, Union

from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import ContainerClient
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
)

from approaches.approach import ThoughtStep
from approaches.chatapproach import ChatApproach
from core.authentication import AuthenticationHelper
from core.imageshelper import fetch_image
from core.modelhelper import get_token_limit


class ChatReadRetrieveReadVisionApproach(ChatApproach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    def __init__(
        self,
        *,
        search_client: SearchClient,
        blob_container_client: ContainerClient,
        openai_client: AsyncOpenAI,
        auth_helper: AuthenticationHelper,
        gpt4v_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        gpt4v_model: str,
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        vision_endpoint: str,
        vision_token_provider: Callable[[], Awaitable[str]]
    ):
        self.search_client = search_client
        self.blob_container_client = blob_container_client
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.gpt4v_deployment = gpt4v_deployment
        self.gpt4v_model = gpt4v_model
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.vision_endpoint = vision_endpoint
        self.vision_token_provider = vision_token_provider
        self.chatgpt_token_limit = get_token_limit(gpt4v_model)

    @property
    def system_message_chat_conversation(self):
        return """
        You are an intelligent assistant helping analyze the Annual Financial Report of Contoso Ltd., The documents contain text, graphs, tables and images.
        Each image source has the file name in the top left corner of the image with coordinates (10,10) pixels and is in the format SourceFileName:<file_name>
        Each text source starts in a new line and has the file name followed by colon and the actual information
        Always include the source name from the image or text for each fact you use in the response in the format: [filename]
        Answer the following question using only the data provided in the sources below.
        If asking a clarifying question to the user would help, ask the question.
        Be brief in your answers.
        For tabular information return it as an html table. Do not return markdown format.
        The text and image source can be the same file name, don't use the image title when citing the image source, only use the file name as mentioned
        If you cannot answer using the sources below, say you don't know. Return just the answer without any input texts.
        {follow_up_questions_prompt}
        {injected_prompt}
        """

    async def run_until_final_call(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]]]:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        vector_fields = overrides.get("vector_fields", ["embedding"])
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top", 3)
        filter = self.build_filter(overrides, auth_claims)
        use_semantic_ranker = True if overrides.get("semantic_ranker") and has_text else False

        include_gtpV_text = overrides.get("gpt4v_input") in ["textAndImages", "texts", None]
        include_gtpV_images = overrides.get("gpt4v_input") in ["textAndImages", "images", None]

        original_user_query = history[-1]["content"]

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        user_query_request = "Generate search query for: " + original_user_query

        messages = self.get_messages_from_history(
            system_prompt=self.query_prompt_template,
            model_id=self.gpt4v_model,
            history=history,
            user_content=user_query_request,
            max_tokens=self.chatgpt_token_limit - len(" ".join(user_query_request)),
            few_shots=self.query_prompt_few_shots,
        )

        chat_completion: ChatCompletion = await self.openai_client.chat.completions.create(
            model=self.gpt4v_deployment if self.gpt4v_deployment else self.gpt4v_model,
            messages=messages,
            temperature=0.0,  # Minimize creativity for search query generation
            max_tokens=100,
            n=1,
        )

        query_text = self.get_search_query(chat_completion, original_user_query)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors = []
        if has_vector:
            for field in vector_fields:
                vector = (
                    await self.compute_text_embedding(query_text)
                    if field == "embedding"
                    else await self.compute_image_embedding(query_text)
                )
                vectors.append(vector)

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        if not has_text:
            query_text = None

        results = await self.search(top, query_text, filter, vectors, use_semantic_ranker, use_semantic_captions)
        sources_content = self.get_sources_content(results, use_semantic_captions, use_image_citation=True)
        content = "\n".join(sources_content)

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the existing prompt using >>>
        system_message = self.get_system_prompt(
            overrides.get("prompt_template"),
            self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else "",
        )

        response_token_limit = 1024
        messages_token_limit = self.chatgpt_token_limit - response_token_limit

        user_content: list[ChatCompletionContentPartParam] = [{"text": original_user_query, "type": "text"}]
        image_list: list[ChatCompletionContentPartImageParam] = []

        if include_gtpV_text:
            user_content.append({"text": "\n\nSources:\n" + content, "type": "text"})
        if include_gtpV_images:
            for result in results:
                url = await fetch_image(self.blob_container_client, result)
                if url:
                    image_list.append({"image_url": url, "type": "image_url"})
            user_content.extend(image_list)

        messages = self.get_messages_from_history(
            system_prompt=system_message,
            model_id=self.gpt4v_model,
            history=history,
            user_content=user_content,
            max_tokens=messages_token_limit,
        )

        data_points = {
            "text": sources_content,
            "images": [d["image_url"] for d in image_list],
        }

        extra_info = {
            "data_points": data_points,
            "thoughts": [
                ThoughtStep(
                    "Original user query",
                    original_user_query,
                ),
                ThoughtStep(
                    "Generated search query",
                    query_text,
                    {"use_semantic_captions": use_semantic_captions, "vector_fields": vector_fields},
                ),
                ThoughtStep("Results", [result.serialize_for_results() for result in results]),
                ThoughtStep("Prompt", [str(message) for message in messages]),
            ],
        }

        chat_coroutine = self.openai_client.chat.completions.create(
            model=self.gpt4v_deployment if self.gpt4v_deployment else self.gpt4v_model,
            messages=messages,
            temperature=overrides.get("temperature", 0.3),
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream,
        )
        return (extra_info, chat_coroutine)
