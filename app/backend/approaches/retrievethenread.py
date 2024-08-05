import ast
from typing import Any, Optional

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageParam
from openai_messages_token_helper import get_token_limit
from promptflow.core import Prompty  # type: ignore

from api_wrappers import LLMClient
from approaches.approach import Approach, ThoughtStep
from core.authentication import AuthenticationHelper
from templates.supported_models import SUPPORTED_MODELS


class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the AI Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    system_chat_template = (
        "You are an intelligent assistant helping Contoso Inc employees with their healthcare plan questions and employee handbook questions. "
        + "Use 'you' to refer to the individual asking the questions even if they ask with 'I'. "
        + "Answer the following question using only the data provided in the sources below. "
        + "For tabular information return it as an html table. Do not return markdown format. "
        + "Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. "
        + "If you cannot answer using the sources below, say you don't know. Use below example to answer"
    )

    # shots/sample conversation
    question = """
'What is the deductible for the employee plan for a visit to Overlake in Bellevue?'

Sources:
info1.txt: deductibles depend on whether you are in-network or out-of-network. In-network deductibles are $500 for employee and $1000 for family. Out-of-network deductibles are $1000 for employee and $2000 for family.
info2.pdf: Overlake is in-network for the employee plan.
info3.pdf: Overlake is the name of the area that includes a park and ride near Bellevue.
info4.pdf: In-network institutions include Overlake, Swedish and others in the region
"""
    answer = "In-network deductibles are $500 for employee and $1000 for family [info1.txt] and Overlake is in-network for the employee plan [info2.pdf][info4.pdf]."

    def __init__(
        self,
        *,
        search_client: SearchClient,
        auth_helper: AuthenticationHelper,
        llm_client: LLMClient,
        emb_client: LLMClient,
        hf_model: Optional[str],  # Not needed for OpenAI
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        embedding_model: str,
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_dimensions: int,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
    ):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.llm_client = llm_client
        self.emb_client = emb_client
        self.hf_model = hf_model
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)

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
        auth_claims = context.get("auth_claims", {})
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        filter = self.build_filter(overrides, auth_claims)

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors: list[VectorQuery] = []
        if use_vector_search:
            vectors.append(await self.compute_text_embedding(q))

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
        )

        # Process results
        sources_content = self.get_sources_content(results, use_semantic_captions, use_image_citation=False)

        # Load the Prompty object
        prompty_path = SUPPORTED_MODELS.get(self.hf_model if self.hf_model else self.chatgpt_model)
        if prompty_path:
            ask_prompty = Prompty.load(source=prompty_path / "ask.prompty")
        else:
            raise ValueError(
                f"Model {self.hf_model if self.hf_model else self.chatgpt_model} is not supported. Please create a template for this model."
            )

        updated_messages = ask_prompty.render(
            system_message=overrides.get("prompt_template", self.system_chat_template),
            question=q,
            sources=sources_content,
        )
        updated_messages = ast.literal_eval(updated_messages)

        # If the parameters are overridden via the API request, use that value.
        # Otherwise, use the default value from the model configuration.
        ask_prompty._model.parameters.update(
            {
                param: overrides[param]
                for param in self.llm_client.allowed_chat_completion_params
                if overrides.get(param) is not None
            }
        )

        chat_completion = await self.llm_client.chat_completion(
            # Azure OpenAI takes the deployment name as the model name
            model=(
                self.hf_model
                if self.hf_model
                else self.chatgpt_deployment if self.chatgpt_deployment else self.chatgpt_model
            ),
            messages=updated_messages,
            **ask_prompty._model.parameters,
            n=1,
        )
        final_result = chat_completion.model_dump() if hasattr(chat_completion, "model_dump") else chat_completion

        data_points = {"text": sources_content}
        extra_info = {
            "data_points": data_points,
            "thoughts": [
                ThoughtStep(
                    "Search using user query",
                    q,
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
                    [str(message) for message in updated_messages],
                    (
                        {"model": self.hf_model}
                        if self.hf_model
                        else (
                            {"model": self.chatgpt_model, "deployment": self.chatgpt_deployment}
                            if self.chatgpt_deployment
                            else {"model": self.chatgpt_model}
                        )
                    ),
                ),
            ],
        }
        completion_message: ChatCompletionMessage
        try:
            if hasattr(final_result, "choices"):
                completion_message = final_result.choices[0].message
            elif isinstance(final_result, dict) and "choices" in final_result:
                completion_message = final_result["choices"][0]["message"]
            else:
                raise TypeError(
                    f"Unexpected chat completion response type: {type(final_result)}. It should be a dictionary or dataclass."
                )
        except Exception as e:
            raise ValueError(f"Failed to retrieve message from chat completion response: {e}")

        completion = {"message": completion_message, "context": extra_info, "session_state": session_state}
        return completion
