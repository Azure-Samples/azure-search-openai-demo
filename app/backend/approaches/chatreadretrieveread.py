import ast
from typing import (
    Any,
    AsyncIterable,
    Coroutine,
    Literal,
    Optional,
    Union,
    overload,
)

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from huggingface_hub.inference._generated.types import (  # type: ignore
    ChatCompletionOutput,
    ChatCompletionStreamOutput,
)
from openai import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)
from promptflow.core import Prompty  # type: ignore

from api_wrappers import LLMClient
from approaches.approach import ThoughtStep
from approaches.chatapproach import ChatApproach
from core.authentication import AuthenticationHelper
from core.messageshelper import build_past_messages
from templates.supported_models import ModelConfig


class ChatReadRetrieveReadApproach(ChatApproach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    def __init__(
        self,
        *,
        search_client: SearchClient,
        auth_helper: AuthenticationHelper,
        llm_clients: dict[str, LLMClient],
        emb_client: LLMClient,
        current_model: str,
        available_models: dict[str, ModelConfig],
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        embedding_dimensions: int,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
    ):
        self.search_client = search_client
        self.llm_clients = llm_clients
        self.emb_client = emb_client
        self.auth_helper = auth_helper
        self.current_model = current_model
        self.available_models = available_models
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller

    @property
    def system_message_chat_conversation(self):
        return """Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.
        Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
        For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
        Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, for example [info1.txt]. Don't combine sources, list each source separately, for example [info1.txt][info2.pdf].
        {follow_up_questions_prompt}
        {injected_prompt}
        """

    @overload
    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[False],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, ChatCompletion]]: ...

    @overload
    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: Literal[True],
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, AsyncStream[ChatCompletionChunk]]]: ...

    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[
        dict[str, Any],
        Coroutine[
            Any,
            Any,
            Union[
                ChatCompletion,
                AsyncStream[ChatCompletionChunk],
                ChatCompletionOutput,
                AsyncIterable[ChatCompletionStreamOutput],
            ],
        ],
    ]:
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False

        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        filter = self.build_filter(overrides, auth_claims)

        model_change = overrides.get("set_model")
        if model_change is not None:
            self.current_model = model_change

        model_config = self.available_models.get(self.current_model)
        if not model_config:
            raise ValueError(f"Model {self.current_model} is not supported. Please create a template for this model.")

        current_api = self.llm_clients[model_config.type]

        original_user_query = messages[-1]["content"]

        if not isinstance(original_user_query, str):
            raise ValueError("The most recent message content must be a string.")

        # Load the Prompty objects for AI Search query and chat answer generation.
        prompty_path = model_config.template_path

        chat_prompty = Prompty.load(source=prompty_path / "chat.prompty")
        query_prompty = Prompty.load(source=prompty_path / "query.prompty")

        # If the parameters are overridden via the API request, use that value.
        # Otherwise, use the default value from the model configuration.
        chat_prompty._model.parameters.update(
            {
                param: overrides[param]
                for param in current_api.allowed_chat_completion_params
                if overrides.get(param) is not None
            }
        )
        # Shorten the past messages if needed
        question_token_limit = chat_prompty._model.configuration.get(
            "messages_length_limit", 4000
        ) - chat_prompty._model.parameters.get("max_tokens", 1024)

        past_messages = build_past_messages(
            model=model_config.model_name,
            model_type=query_prompty._model.configuration["type"],
            system_message=self.query_prompt_template,
            max_tokens=question_token_limit,
            tools=query_prompty._model.parameters.get("tools"),
            new_user_content=original_user_query,
            few_shots=self.query_prompt_few_shots,
            past_messages=messages[:-1],
        )
        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        query_messages = query_prompty.render(
            system_message=self.query_prompt_template,
            question=original_user_query,
            few_shots=self.query_prompt_few_shots,
            past_messages=past_messages,
        )
        query_messages = ast.literal_eval(query_messages)

        # If the temperature is not set in the config, use default value equal to 0.0
        query_prompty._model.parameters.setdefault("temperature", 0.0)
        chat_completion: Union[ChatCompletion, ChatCompletionOutput, AsyncIterable[ChatCompletionStreamOutput]] = (
            await current_api.chat_completion(
                messages=query_messages,  # type: ignore
                model=(model_config.identifier),
                **query_prompty._model.parameters,
                n=1,
            )
        )
        query_text = self.get_search_query(chat_completion, original_user_query)
        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors: list[VectorQuery] = []
        if use_vector_search:
            vectors.append(await self.compute_text_embedding(query_text))

        results = await self.search(
            top,
            query_text,
            filter,
            vectors,
            use_text_search,
            use_vector_search,
            use_semantic_ranker,
            use_semantic_captions,
            minimum_search_score,
            minimum_reranker_score,
        )

        sources_content = self.get_sources_content(results, use_semantic_captions, use_image_citation=False)

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        system_message = self.get_system_prompt(
            overrides.get("prompt_template"),
            self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else "",
        )

        chat_messages = chat_prompty.render(
            system_message=system_message,
            sources=sources_content,
            past_messages=past_messages,
            question=original_user_query,
        )
        chat_messages = ast.literal_eval(chat_messages)

        data_points = {"text": sources_content}

        extra_info = {
            "data_points": data_points,
            "thoughts": [
                ThoughtStep(
                    "Prompt to generate search query",
                    [str(message) for message in query_messages],
                    ({"model": self.current_model}),
                ),
                ThoughtStep(
                    "Search using generated search query",
                    query_text,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "top": top,
                        "filter": filter,
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
                    [str(message) for message in chat_messages],
                    ({"model": self.current_model}),
                ),
            ],
        }

        chat_coroutine = current_api.chat_completion(
            model=(model_config.identifier),
            messages=chat_messages,
            **chat_prompty._model.parameters,
            n=1,
            stream=should_stream,
        )
        return (extra_info, chat_coroutine)
