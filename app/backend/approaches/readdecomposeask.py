import re
from typing import Any, Optional, Sequence

import openai
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType
from langchain.agents import AgentExecutor, Tool
from langchain.agents.react.base import ReActDocstoreAgent
from langchain.callbacks.manager import CallbackManager
from langchain.llms.openai import AzureOpenAI
from langchain.prompts import BasePromptTemplate, PromptTemplate
from langchain.tools.base import BaseTool

from approaches.approach import AskApproach
from langchainadapters import HtmlCallbackHandler
from text import nonewlines


class ReadDecomposeAsk(AskApproach):
    def __init__(self, search_client: SearchClient, openai_deployment: str, embedding_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    async def search(self, query_text: str, overrides: dict[str, Any]) -> tuple[list[str], str]:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        # If retrieval mode includes vectors, compute an embedding for the query
        if has_vector:
            query_vector = (await openai.Embedding.acreate(engine=self.embedding_deployment, input=query_text))["data"][0]["embedding"]
        else:
            query_vector = None

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        if not has_text:
            query_text = ""

        if overrides.get("semantic_ranker") and has_text:
            r = await self.search_client.search(query_text,
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC,
                                          query_language="en-us",
                                          query_speller="lexicon",
                                          semantic_configuration_name="default",
                                          top=top,
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None,
                                          vector=query_vector,
                                          top_k=50 if query_vector else None,
                                          vector_fields="embedding" if query_vector else None)
        else:
            r = await self.search_client.search(query_text,
                                          filter=filter,
                                          top=top,
                                          vector=query_vector,
                                          top_k=50 if query_vector else None,
                                          vector_fields="embedding" if query_vector else None)
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ":" + nonewlines(" . ".join([c.text for c in doc['@search.captions'] ])) async for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ":" + nonewlines(doc[self.content_field][:500]) async for doc in r]
        return results, "\n".join(results)

    async def lookup(self, q: str) -> Optional[str]:
        r = await self.search_client.search(q,
                                      top = 1,
                                      include_total_count=True,
                                      query_type=QueryType.SEMANTIC,
                                      query_language="en-us",
                                      query_speller="lexicon",
                                      semantic_configuration_name="default",
                                      query_answer="extractive|count-1",
                                      query_caption="extractive|highlight-false")

        answers = await r.get_answers()
        if answers and len(answers) > 0:
            return answers[0].text
        if await r.get_count() > 0:
            return "\n".join([d['content'] async for d in r])
        return None

    async def run(self, q: str, overrides: dict[str, Any]) -> dict[str, Any]:

        search_results = None
        async def search_and_store(q: str) -> Any:
            nonlocal search_results
            search_results, content = await self.search(q, overrides)
            return content

        # Use to capture thought process during iterations
        cb_handler = HtmlCallbackHandler()
        cb_manager = CallbackManager(handlers=[cb_handler])

        llm = AzureOpenAI(deployment_name=self.openai_deployment, temperature=overrides.get("temperature") or 0.3, openai_api_key=openai.api_key)
        tools = [
            Tool(name="Search", func=lambda _: 'Not implemented', coroutine=search_and_store, description="useful for when you need to ask with search", callbacks=cb_manager),
            Tool(name="Lookup", func=lambda _: 'Not implemented', coroutine=self.lookup, description="useful for when you need to ask with lookup", callbacks=cb_manager)
        ]

        prompt_prefix = overrides.get("prompt_template")
        prompt = PromptTemplate.from_examples(
            EXAMPLES, SUFFIX, ["input", "agent_scratchpad"], prompt_prefix + "\n\n" + PREFIX if prompt_prefix else PREFIX)

        class ReAct(ReActDocstoreAgent):
            @classmethod
            def create_prompt(cls, tools: Sequence[BaseTool]) -> BasePromptTemplate:
                return prompt

        agent = ReAct.from_llm_and_tools(llm, tools)
        chain = AgentExecutor.from_agent_and_tools(agent, tools, verbose=True, callback_manager=cb_manager)
        result = await chain.arun(q)

        # Replace substrings of the form <file.ext> with [file.ext] so that the frontend can render them as links, match them with a regex to avoid
        # generalizing too much and disrupt HTML snippets if present
        result = re.sub(r"<([a-zA-Z0-9_ \-\.]+)>", r"[\1]", result)

        return {"data_points": search_results or [], "answer": result, "thoughts": cb_handler.get_and_reset_log()}



# Modified version of langchain's ReAct prompt that includes instructions and examples for how to cite information sources
EXAMPLES = [
    """Question: What is the elevation range for the area that the eastern sector of the
Colorado orogeny extends into?
Thought: I need to search Colorado orogeny, find the area that the eastern sector
of the Colorado orogeny extends into, then find the elevation range of the
area.
Action: Search[Colorado orogeny]
Observation: <info1.pdf> The Colorado orogeny was an episode of mountain building (an orogeny) in
Colorado and surrounding areas.
Thought: It does not mention the eastern sector. So I need to look up eastern
sector.
Action: Lookup[eastern sector]
Observation: <info2.txt> (Result 1 / 1) The eastern sector extends into the High Plains and is called
the Central Plains orogeny.
Thought: The eastern sector of Colorado orogeny extends into the High Plains. So I
need to search High Plains and find its elevation range.
Action: Search[High Plains]
Observation: <some_file.pdf> High Plains refers to one of two distinct land regions
Thought: I need to instead search High Plains (United States).
Action: Search[High Plains (United States)]
Observation: <filea.pdf> The High Plains are a subregion of the Great Plains. <another-ref.docx> From east to west, the
High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130
m).
Thought: High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer
is 1,800 to 7,000 ft.
Action: Finish[1,800 to 7,000 ft <filea.pdf>]""",
    """Question: Musician and satirist Allie Goertz wrote a song about the "The Simpsons"
character Milhouse, who Matt Groening named after who?
Thought: The question simplifies to "The Simpsons" character Milhouse is named after
who. I only need to search Milhouse and find who it is named after.
Action: Search[Milhouse]
Observation: <info7.pdf> Milhouse Mussolini Van Houten is a recurring character in the Fox animated
television series The Simpsons voiced by Pamela Hayden and created by Matt
Groening.
Thought: The paragraph does not tell who Milhouse is named after, maybe I can look up
"named after".
Action: Lookup[named after]
Observation: <historyref2.txt> (Result 1 / 1) Milhouse was named after U.S. president Richard Nixon, whose
middle name was Milhous.
Thought: Milhouse was named after U.S. president Richard Nixon, so the answer is
Richard Nixon.
Action: Finish[Richard Nixon <historyref2.txt>]""",
    """Question: Which documentary is about Finnish rock groups, Adam Clayton Powell or The
Saimaa Gesture?
Thought: I need to search Adam Clayton Powell and The Saimaa Gesture, and find which
documentary is about Finnish rock groups.
Action: Search[Adam Clayton Powell]
Observation: <info9.pdf> Could not find [Adam Clayton Powell]. Similar: ['Adam Clayton Powell
III', 'Seventh Avenue (Manhattan)', 'Adam Clayton Powell Jr. State Office
Building', 'Isabel Washington Powell', 'Adam Powell', vAdam Clayton Powell
(film)', 'Giancarlo Esposito'].
Thought: To find the documentary, I can search Adam Clayton Powell (film).
Action: Search[Adam Clayton Powell (film)]
Observation: <data123.txt> Adam Clayton Powell is a 1989 American documentary film directed by
Richard Kilberg. The film is about the rise and fall of influential
African-American politician Adam Clayton Powell Jr.[3][4] It was later aired
as part of the PBS series The American Experience.
Thought: Adam Clayton Powell (film) is a documentary about an African-American
politician, not Finnish rock groups. So the documentary about Finnish rock
groups must instead be The Saimaa Gesture.
Action: Finish[The Saimaa Gesture <data123.txt>]""",
    """Question: What profession does Nicholas Ray and Elia Kazan have in common?
Thought: I need to search Nicholas Ray and Elia Kazan, find their professions, then
find the profession they have in common.
Action: Search[Nicholas Ray]
Observation: <files-987.png> Nicholas Ray (born Raymond Nicholas Kienzle Jr., August 7, 1911 - June 16,
1979) was an American film director, screenwriter, and actor best known for
the 1955 film Rebel Without a Cause.
Thought: Professions of Nicholas Ray are director, screenwriter, and actor. I need
to search Elia Kazan next and find his professions.
Action: Search[Elia Kazan]
Observation: <files-654.txt> Elia Kazan was an American film and theatre director, producer, screenwriter
and actor.
Thought: Professions of Elia Kazan are director, producer, screenwriter, and actor.
So profession Nicholas Ray and Elia Kazan have in common is director,
screenwriter, and actor.
Action: Finish[director, screenwriter, actor <files-987.png><files-654.txt>]""",
    """Question: Which magazine was started first Arthur's Magazine or First for Women?
Thought: I need to search Arthur's Magazine and First for Women, and find which was
started first.
Action: Search[Arthur's Magazine]
Observation: <magazines-1850.pdf> Arthur's Magazine (1844-1846) was an American literary periodical published
in Philadelphia in the 19th century.
Thought: Arthur's Magazine was started in 1844. I need to search First for Women
next.
Action: Search[First for Women]
Observation: <magazines-1900.pdf> First for Women is a woman's magazine published by Bauer Media Group in the
USA.[1] The magazine was started in 1989.
Thought: First for Women was started in 1989. 1844 (Arthur's Magazine) < 1989 (First
for Women), so Arthur's Magazine was started first.
Action: Finish[Arthur's Magazine <magazines-1850.pdf><magazines-1900.pdf>]""",
    """Question: Were Pavel Urysohn and Leonid Levin known for the same type of work?
Thought: I need to search Pavel Urysohn and Leonid Levin, find their types of work,
then find if they are the same.
Action: Search[Pavel Urysohn]
Observation: <info4444.pdf> Pavel Samuilovich Urysohn (February 3, 1898 - August 17, 1924) was a Soviet
mathematician who is best known for his contributions in dimension theory.
Thought: Pavel Urysohn is a mathematician. I need to search Leonid Levin next and
find its type of work.
Action: Search[Leonid Levin]
Observation: <datapoints_aaa.txt> Leonid Anatolievich Levin is a Soviet-American mathematician and computer
scientist.
Thought: Leonid Levin is a mathematician and computer scientist. So Pavel Urysohn
and Leonid Levin have the same type of work.
Action: Finish[yes <info4444.pdf><datapoints_aaa.txt>]""",
]
SUFFIX = """\nQuestion: {input}
{agent_scratchpad}"""
PREFIX = "Answer questions as shown in the following examples, by splitting the question into individual search or lookup actions to find facts until you can answer the question. " \
"Observations are prefixed by their source name in angled brackets, source names MUST be included with the actions in the answers." \
"All questions must be answered from the results from search or look up actions, only facts resulting from those can be used in an answer. "
"Answer questions as truthfully as possible, and ONLY answer the questions using the information from observations, do not speculate or your own knowledge."
