import re
from typing import Any, Optional, Sequence

import openai
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType
from langchain.agents import AgentExecutor, Tool
from langchain.agents.react.base import ReActDocstoreAgent
from langchain.callbacks.manager import CallbackManager
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts import BasePromptTemplate, PromptTemplate
from langchain.tools.base import BaseTool

from approaches.approach import AskApproach
from langchainadapters import HtmlCallbackHandler
from text import nonewlines


class ReadDecomposeAsk(AskApproach):
    def __init__(
        self,
        search_client: SearchClient,
        openai_host: str,
        openai_deployment: str,
        openai_model: str,
        embedding_deployment: str,
        embedding_model: str,
        sourcepage_field: str,
        content_field: str,
    ):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.openai_model = openai_model
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.openai_host = openai_host

    async def search(
        self, query_text: str, overrides: dict[str, Any], auth_claims: dict[str, Any]
    ) -> tuple[list[str], str]:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top", 3)
        filter = self.build_filter(overrides, auth_claims)

        # If retrieval mode includes vectors, compute an embedding for the query
        if has_vector:
            embedding_args = {"deployment_id": self.embedding_deployment} if self.openai_host == "azure" else {}
            embedding = await openai.Embedding.acreate(**embedding_args, model=self.embedding_model, input=query_text)
            query_vector = embedding["data"][0]["embedding"]
        else:
            query_vector = None

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        if not has_text:
            query_text = ""

        if overrides.get("semantic_ranker") and has_text:
            r = await self.search_client.search(
                query_text,
                filter=filter,
                query_type=QueryType.SEMANTIC,
                query_language="en-us",
                query_speller="lexicon",
                semantic_configuration_name="default",
                top=top,
                query_caption="extractive|highlight-false" if use_semantic_captions else None,
                vector=query_vector,
                top_k=50 if query_vector else None,
                vector_fields="embedding" if query_vector else None,
            )
        else:
            r = await self.search_client.search(
                query_text,
                filter=filter,
                top=top,
                vector=query_vector,
                top_k=50 if query_vector else None,
                vector_fields="embedding" if query_vector else None,
            )
        if use_semantic_captions:
            self.results = [
                doc[self.sourcepage_field] + ":" + nonewlines(" . ".join([c.text for c in doc["@search.captions"]]))
                async for doc in r
            ]
        else:
            results = [doc[self.sourcepage_field] + ":" + nonewlines(doc[self.content_field][:500]) async for doc in r]
        return results, "\n".join(results)

    async def lookup(self, q: str) -> Optional[str]:
        r = await self.search_client.search(
            q,
            top=1,
            include_total_count=True,
            query_type=QueryType.SEMANTIC,
            query_language="en-us",
            query_speller="lexicon",
            semantic_configuration_name="default",
            query_answer="extractive|count-1",
            query_caption="extractive|highlight-false",
        )

        answers = await r.get_answers()
        if answers and len(answers) > 0:
            return answers[0].text
        if await r.get_count() > 0:
            return "\n".join([d["content"] async for d in r])
        return None

    async def run(self, q: str, overrides: dict[str, Any], auth_claims: dict[str, Any]) -> dict[str, Any]:
        search_results = None

        async def search_and_store(q: str) -> Any:
            nonlocal search_results
            search_results, content = await self.search(q, overrides, auth_claims)
            return content

        # Use to capture thought process during iterations
        cb_handler = HtmlCallbackHandler()
        cb_manager = CallbackManager(handlers=[cb_handler])

        llm = AzureChatOpenAI(deployment_name=self.openai_deployment, openai_api_version=openai.api_version,
                          openai_api_key=openai.api_key, openai_api_type=openai.api_type,
                          openai_api_base=openai.api_base)
        tools = [
            Tool(
                name="Search",
                func=lambda _: "Not implemented",
                coroutine=search_and_store,
                description="useful for when you need to ask with search",
                callbacks=cb_manager,
            ),
            Tool(
                name="Lookup",
                func=lambda _: "Not implemented",
                coroutine=self.lookup,
                description="useful for when you need to ask with lookup",
                callbacks=cb_manager,
            ),
        ]

        prompt_prefix = overrides.get("prompt_template")
        prompt = PromptTemplate.from_examples(
            EXAMPLES,
            SUFFIX,
            ["input", "agent_scratchpad"],
            prompt_prefix + "\n\n" + PREFIX if prompt_prefix else PREFIX,
        )

        class ReAct(ReActDocstoreAgent):
            @classmethod
            def create_prompt(cls, tools: Sequence[BaseTool]) -> BasePromptTemplate:
                return prompt

        agent = ReAct.from_llm_and_tools(llm, tools)
        chain = AgentExecutor.from_agent_and_tools(agent, tools, verbose=True, handle_parsing_errors=True, callback_manager=cb_manager)
        result = await chain.arun(q)

        # Replace substrings of the form <file.ext> with [file.ext] so that the frontend can render them as links, match them with a regex to avoid
        # generalizing too much and disrupt HTML snippets if present
        result = re.sub(r"<([a-zA-Z0-9_ \-\.]+)>", r"[\1]", result)

        return {"data_points": search_results or [], "answer": result, "thoughts": cb_handler.get_and_reset_log()}