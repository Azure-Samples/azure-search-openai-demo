from typing import Any, Optional

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai_messages_token_helper import build_messages, get_token_limit

from approaches.approach import Approach, ThoughtStep
from core.authentication import AuthenticationHelper


class RetrieveThenReadApproach(Approach):
    """
    Simple retrieve-then-read implementation, using the AI Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """

    system_chat_template = (
    "You are an intelligent assistant helping Al Ghurair employees understand their policies as employees of the company."
    + "Use 'you' to refer to the individual asking the questions even if they ask with 'I'. "
    + "Answer the following question using the data provided in all available indexed sources. "
    + "For tabular information return it as an html table. Do not return markdown format. "
    + "Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. "
    + "If you cannot answer using the available sources, say you don't know. Use the example below to answer."
    )
    
    # shots/sample conversation
    question = """
'What is the policy for handling backup tapes?'

Sources:
info1.pdf: All Group’s business information, applications and information systems must be backed up. Group IT will define the type (full, incremental, or differential) and frequency of backups depending on the business and security requirements of the information involved. Availability and recovery of data at rest on workstations and laptops cannot be assured unless this data is backed up by the respective users on to a central storage provided to them.
info2.pdf: Uniform labelling convention must be used for labelling backup media. Based on classification and criticality, backup tapes must be moved to an offsite location at a predefined interval. All backup equipment and tapes must be given adequate physical protection i.e. locked fireproof cabinets, both on offsite and on-site locations.
"""
    answer = "All backup tapes must be labelled uniformly and moved to an offsite location at predefined intervals. Backup equipment and tapes must be stored in locked fireproof cabinets both on-site and offsite [info1.pdf][info2.pdf]."

    def __init__(
        self,
        *,
        search_client: SearchClient,
        auth_helper: AuthenticationHelper,
        openai_client: AsyncOpenAI,
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
        self.openai_client = openai_client
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

        # Append user message
        content = "\n".join(sources_content)
        user_content = q + "\n" + f"Sources:\n {content}"

        response_token_limit = 1024
        updated_messages = build_messages(
            model=self.chatgpt_model,
            system_prompt=overrides.get("prompt_template", self.system_chat_template),
            few_shots=[{"role": "user", "content": self.question}, {"role": "assistant", "content": self.answer}],
            new_user_content=user_content,
            max_tokens=self.chatgpt_token_limit - response_token_limit,
        )

        chat_completion = (
            await self.openai_client.chat.completions.create(
                # Azure OpenAI takes the deployment name as the model name
                model=self.chatgpt_deployment if self.chatgpt_deployment else self.chatgpt_model,
                messages=updated_messages,
                temperature=overrides.get("temperature", 0.3),
                max_tokens=response_token_limit,
                n=1,
            )
        ).model_dump()

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
                        {"model": self.chatgpt_model, "deployment": self.chatgpt_deployment}
                        if self.chatgpt_deployment
                        else {"model": self.chatgpt_model}
                    ),
                ),
            ],
        }

        completion = {}
        completion["message"] = chat_completion["choices"][0]["message"]
        completion["context"] = extra_info
        completion["session_state"] = session_state
        return completion
