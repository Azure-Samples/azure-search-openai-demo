import openai
from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from langchain.llms.openai import AzureOpenAI
from langchain.prompts import PromptTemplate, BasePromptTemplate
from langchain.callbacks.base import CallbackManager
from langchain.agents import Tool, AgentExecutor
from langchain.agents.react.base import ReActDocstoreAgent
from langchainadapters import HtmlCallbackHandler
from text import nonewlines
from typing import List

class ReadDecomposeAsk(Approach):
    def __init__(self, search_client: SearchClient, openai_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def search(self, q: str, overrides: dict) -> str:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        if overrides.get("semantic_ranker"):
            r = self.search_client.search(q,
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language="en-us", 
                                          query_speller="lexicon", 
                                          semantic_configuration_name="default", 
                                          top = top,
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(q, filter=filter, top=top)
        if use_semantic_captions:
            self.results = [doc[self.sourcepage_field] + ":" + nonewlines(" . ".join([c.text for c in doc['@search.captions'] ])) for doc in r]
        else:
            self.results = [doc[self.sourcepage_field] + ":" + nonewlines(doc[self.content_field][:500]) for doc in r]
        return "\n".join(self.results)

    def lookup(self, q: str) -> str:
        r = self.search_client.search(q,
                                      top = 1,
                                      include_total_count=True,
                                      query_type=QueryType.SEMANTIC, 
                                      query_language="en-us", 
                                      query_speller="lexicon", 
                                      semantic_configuration_name="default",
                                      query_answer="extractive|count-1",
                                      query_caption="extractive|highlight-false")
        
        answers = r.get_answers()
        if answers and len(answers) > 0:
            return answers[0].text
        if r.get_count() > 0:
            return "\n".join(d['content'] for d in r)
        return None        

    def run(self, q: str, overrides: dict) -> any:
        # Not great to keep this as instance state, won't work with interleaving (e.g. if using async), but keeps the example simple
        self.results = None

        # Use to capture thought process during iterations
        cb_handler = HtmlCallbackHandler()
        cb_manager = CallbackManager(handlers=[cb_handler])

        llm = AzureOpenAI(deployment_name=self.openai_deployment, temperature=overrides.get("temperature") or 0.3, openai_api_key=openai.api_key)
        tools = [
            Tool(name="Search", func=lambda q: self.search(q, overrides)),
            Tool(name="Lookup", func=self.lookup)
        ]

        # Like results above, not great to keep this as a global, will interfere with interleaving
        global prompt
        prompt_prefix = overrides.get("prompt_template")
        prompt = PromptTemplate.from_examples(
            EXAMPLES, SUFFIX, ["input", "agent_scratchpad"], prompt_prefix + "\n\n" + PREFIX if prompt_prefix else PREFIX)

        agent = ReAct.from_llm_and_tools(llm, tools)
        chain = AgentExecutor.from_agent_and_tools(agent, tools, verbose=True, callback_manager=cb_manager)
        result = chain.run(q)

        # Fix up references to they look like what the frontend expects ([] instead of ()), need a better citation format since parentheses are so common
        result = result.replace("(", "[").replace(")", "]")

        return {"data_points": self.results or [], "answer": result, "thoughts": cb_handler.get_and_reset_log()}
    
class ReAct(ReActDocstoreAgent):
    @classmethod
    def create_prompt(cls, tools: List[Tool]) -> BasePromptTemplate:
        return prompt
    
# Modified version of langchain's ReAct prompt that includes instructions and examples for how to cite information sources
EXAMPLES = [
    """Question: What is the elevation range for the area that the eastern sector of the
Colorado orogeny extends into?
Thought 1: I need to search Colorado orogeny, find the area that the eastern sector
of the Colorado orogeny extends into, then find the elevation range of the
area.
Action 1: Search[Colorado orogeny]
Observation 1: [info1.pdf] The Colorado orogeny was an episode of mountain building (an orogeny) in
Colorado and surrounding areas.
Thought 2: It does not mention the eastern sector. So I need to look up eastern
sector.
Action 2: Lookup[eastern sector]
Observation 2: [info2.txt] (Result 1 / 1) The eastern sector extends into the High Plains and is called
the Central Plains orogeny.
Thought 3: The eastern sector of Colorado orogeny extends into the High Plains. So I
need to search High Plains and find its elevation range.
Action 3: Search[High Plains]
Observation 3: [some_file.pdf] High Plains refers to one of two distinct land regions
Thought 4: I need to instead search High Plains (United States).
Action 4: Search[High Plains (United States)]
Observation 4: [filea.pdf] The High Plains are a subregion of the Great Plains. [another-ref.docx] From east to west, the
High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130
m).
Thought 5: High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer
is 1,800 to 7,000 ft.
Action 5: Finish[1,800 to 7,000 ft (filea.pdf) ]""",
    """Question: Musician and satirist Allie Goertz wrote a song about the "The Simpsons"
character Milhouse, who Matt Groening named after who?
Thought 1: The question simplifies to "The Simpsons" character Milhouse is named after
who. I only need to search Milhouse and find who it is named after.
Action 1: Search[Milhouse]
Observation 1: [info7.pdf] Milhouse Mussolini Van Houten is a recurring character in the Fox animated
television series The Simpsons voiced by Pamela Hayden and created by Matt
Groening.
Thought 2: The paragraph does not tell who Milhouse is named after, maybe I can look up
"named after".
Action 2: Lookup[named after]
Observation 2: [historyref2.txt] (Result 1 / 1) Milhouse was named after U.S. president Richard Nixon, whose
middle name was Milhous.
Thought 3: Milhouse was named after U.S. president Richard Nixon, so the answer is
Richard Nixon.
Action 3: Finish[Richard Nixon (historyref2.txt) ]""",
    """Question: Which documentary is about Finnish rock groups, Adam Clayton Powell or The
Saimaa Gesture?
Thought 1: I need to search Adam Clayton Powell and The Saimaa Gesture, and find which
documentary is about Finnish rock groups.
Action 1: Search[Adam Clayton Powell]
Observation 1: [info9.pdf] Could not find [Adam Clayton Powell]. Similar: ['Adam Clayton Powell
III', 'Seventh Avenue (Manhattan)', 'Adam Clayton Powell Jr. State Office
Building', 'Isabel Washington Powell', 'Adam Powell', vAdam Clayton Powell
(film)', 'Giancarlo Esposito'].
Thought 2: To find the documentary, I can search Adam Clayton Powell (film).
Action 2: Search[Adam Clayton Powell (film)]
Observation 2: [data123.txt] Adam Clayton Powell is a 1989 American documentary film directed by
Richard Kilberg. The film is about the rise and fall of influential
African-American politician Adam Clayton Powell Jr.[3][4] It was later aired
as part of the PBS series The American Experience.
Thought 3: Adam Clayton Powell (film) is a documentary about an African-American
politician, not Finnish rock groups. So the documentary about Finnish rock
groups must instead be The Saimaa Gesture.
Action 3: Finish[The Saimaa Gesture (data123.txt) ]""",
    """Question: What profession does Nicholas Ray and Elia Kazan have in common?
Thought 1: I need to search Nicholas Ray and Elia Kazan, find their professions, then
find the profession they have in common.
Action 1: Search[Nicholas Ray]
Observation 1: [files-987.png] Nicholas Ray (born Raymond Nicholas Kienzle Jr., August 7, 1911 - June 16,
1979) was an American film director, screenwriter, and actor best known for
the 1955 film Rebel Without a Cause.
Thought 2: Professions of Nicholas Ray are director, screenwriter, and actor. I need
to search Elia Kazan next and find his professions.
Action 2: Search[Elia Kazan]
Observation 2: [files-654.txt] Elia Kazan was an American film and theatre director, producer, screenwriter
and actor.
Thought 3: Professions of Elia Kazan are director, producer, screenwriter, and actor.
So profession Nicholas Ray and Elia Kazan have in common is director,
screenwriter, and actor.
Action 3: Finish[director, screenwriter, actor (files-987.png)(files-654.txt) ]""",
    """Question: Which magazine was started first Arthur's Magazine or First for Women?
Thought 1: I need to search Arthur's Magazine and First for Women, and find which was
started first.
Action 1: Search[Arthur's Magazine]
Observation 1: [magazines-1850.pdf] Arthur's Magazine (1844-1846) was an American literary periodical published
in Philadelphia in the 19th century.
Thought 2: Arthur's Magazine was started in 1844. I need to search First for Women
next.
Action 2: Search[First for Women]
Observation 2: [magazines-1900.pdf] First for Women is a woman's magazine published by Bauer Media Group in the
USA.[1] The magazine was started in 1989.
Thought 3: First for Women was started in 1989. 1844 (Arthur's Magazine) < 1989 (First
for Women), so Arthur's Magazine was started first.
Action 3: Finish[Arthur's Magazine (magazines-1850.pdf)(magazines-1900.pdf) ]""",
    """Question: Were Pavel Urysohn and Leonid Levin known for the same type of work?
Thought 1: I need to search Pavel Urysohn and Leonid Levin, find their types of work,
then find if they are the same.
Action 1: Search[Pavel Urysohn]
Observation 1: [info4444.pdf] Pavel Samuilovich Urysohn (February 3, 1898 - August 17, 1924) was a Soviet
mathematician who is best known for his contributions in dimension theory.
Thought 2: Pavel Urysohn is a mathematician. I need to search Leonid Levin next and
find its type of work.
Action 2: Search[Leonid Levin]
Observation 2: [datapoints_aaa.txt] Leonid Anatolievich Levin is a Soviet-American mathematician and computer
scientist.
Thought 3: Leonid Levin is a mathematician and computer scientist. So Pavel Urysohn
and Leonid Levin have the same type of work.
Action 3: Finish[yes (info4444.pdf)(datapoints_aaa.txt) ]""",
]
SUFFIX = """\nQuestion: {input}
{agent_scratchpad}"""
PREFIX = "Answer questions as shown in the following examples, by splitting the question into individual search or lookup actions to find facts until you can answer the question. " \
"Observations are prefixed by their source name in square brackets, source names MUST be included with the actions in the answers." \
"Only answer the questions using the information from observations, do not speculate."
