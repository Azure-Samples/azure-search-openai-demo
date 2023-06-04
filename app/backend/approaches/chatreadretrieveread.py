import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class ChatReadRetrieveReadApproach(Approach):
    prompt_prefix = """<|im_start|>system
You are a virtual assistant of LIC, the biggest insurance company in India. Assistant helps the interested coustomer with their policy related queries. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
{follow_up_questions_prompt}
{injected_prompt}
Sources:
{sources}
<|im_end|>
{chat_history}
"""

    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next about the policy documents. 
    Use double angle brackets to reference the questions, e.g. <<What is the maximum number of nominees I can add for this policy?>>.
    Try not to repeat questions that have already been asked.
    Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about LIC policy documents.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.

Chat History:
{chat_history}

Question:
{question}

Search query:
"""

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, gpt_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def run(self, history: list[dict], overrides: dict) -> any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        prompt = self.query_prompt_template.format(chat_history=self.get_chat_history_as_text(history, include_last_turn=False), question=history[-1]["user"])
        completion = openai.Completion.create(
            engine=self.gpt_deployment, # using GPT-3 davinci model deployment
            prompt=prompt, 
            temperature=0.0, # temperature for deterministic output https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
            max_tokens=32, # Setting it low to get a short and crisp search prompt for cognitive search
            n=1, # number of completions to generate
            stop=["\n"]) #The stop parameter allows you to specify a stopping condition for the generated output. You can provide a string or an array of strings, and when the model generates any of these strings, it will stop generating text.
        q = completion.choices[0].text

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
        if overrides.get("semantic_ranker"):
            r = self.search_client.search(q, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, # seantic type allows to understand the meaning of query ratehr than focusing on keywords
                                          query_language="en-us", # language
                                          query_speller="lexicon", # spell checker
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(q, filter=filter, top=top)
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        follow_up_questions_prompt = self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else ""
        
        # Preparing prompt for gpt-3.5 model
        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None: # To replace the whole prompt using prompt_override
            prompt = self.prompt_prefix.format(injected_prompt="", 
                                               sources=content, 
                                               chat_history=self.get_chat_history_as_text(history), 
                                               follow_up_questions_prompt=follow_up_questions_prompt)# asking gpt-3.5 for 3 follow-up questions
        elif prompt_override.startswith(">>>"): # To add custom prompt using ">>>"
            prompt = self.prompt_prefix.format(injected_prompt=prompt_override[3:] + "\n", 
                                               sources=content, 
                                               chat_history=self.get_chat_history_as_text(history), 
                                               follow_up_questions_prompt=follow_up_questions_prompt)# asking gpt-3.5 for 3 follow-up questions
        else: #To go with existing prompt
            prompt = prompt_override.format(sources=content, 
                                            chat_history=self.get_chat_history_as_text(history), 
                                            follow_up_questions_prompt=follow_up_questions_prompt) # asking gpt-3.5 for 3 follow-up questions

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        completion = openai.Completion.create( # though we are using gpt-3.5-turbo we are using Completion not Chat
            engine=self.chatgpt_deployment, # using GPT-3.5-turbo model deployment
            prompt=prompt, # prompt is in a string format containing system messages, cognitive search extracted data, chat history
            temperature=overrides.get("temperature") or 0.7, # temperature for creative writing https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
            max_tokens=1024, 
            n=1, 
            stop=["<|im_end|>", "<|im_start|>"])

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Searched for:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
    
    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=1000) -> str:
        #include_last_turn decides to include the the last question ot not
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = """<|im_start|>user""" +"\n" + h["user"] + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>assistant""" + "\n" + (h.get("bot") + """<|im_end|>""" if h.get("bot") else "") + "\n" + history_text
            if len(history_text) > approx_max_tokens*4:
                break    
        return history_text