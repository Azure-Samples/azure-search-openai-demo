from typing import Any, Sequence

import openai
import tiktoken
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines

class ChatReadRetrieveReadApproach(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """
    system_message_chat_conversation = """Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
{follow_up_questions_prompt}
{injected_prompt}
"""
    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next about their healthcare plan and employee handbook. 
Use double angle brackets to reference the questions, e.g. <<Are there exclusions for prescriptions?>>.
Try not to repeat questions that have already been asked.
Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    query_prompt_template = """Chat History:
{chat_history}

Question:
{question}

Given the above chat history and user question generate a search query that will return the best answer from the knowledge base.
Try and generate a grammatical sentence for the search query.
Do NOT use quotes and avoid other search operators.
Do not include cited source filenames and document names such as info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Generate the search query in English even if the questions are not in English.

Search query:
"""

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, chatgpt_model: str, gpt_deployment: str, embedding_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.gpt_deployment = gpt_deployment
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        prompt = self.query_prompt_template.format(chat_history=self.get_chat_history_as_text(history, include_last_turn=False), question=history[-1]["user"])
        completion = openai.Completion.create(
            engine=self.gpt_deployment, 
            prompt=prompt, 
            temperature=0.0, 
            max_tokens=32, 
            n=1, 
            stop=["\n"])
        query_text = completion.choices[0].text

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query
        if has_vector:
            query_vector = openai.Embedding.create(engine=self.embedding_deployment, input=query_text)["data"][0]["embedding"]
        else:
            query_vector = None

         # Only keep the text query if the retrieval mode uses text, otherwise drop it
        if not has_text:
            query_text = None

        # Use semantic L2 reranker if requested and if retrieval mode is text or hybrid (vectors + text)
        if overrides.get("semantic_ranker") and has_text:
            r = self.search_client.search(query_text, 
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
            r = self.search_client.search(query_text, 
                                          filter=filter, 
                                          top=top, 
                                          vector=query_vector, 
                                          top_k=50 if query_vector else None, 
                                          vector_fields="embedding" if query_vector else None)
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        follow_up_questions_prompt = self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else ""
        
        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        messages = self.get_messages_from_history(prompt_override=prompt_override, follow_up_questions_prompt=follow_up_questions_prompt,history=history, sources=content)

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        chat_completion = openai.ChatCompletion.create(
            deployment_id=self.chatgpt_deployment,
            model=self.chatgpt_model,
            messages=messages, 
            temperature=overrides.get("temperature") or 0.7, 
            max_tokens=1024, 
            n=1)
        
        chat_content = chat_completion.choices[0].message.content

        msg_to_display = '\n\n'.join([str(message) for message in messages])

        return {"data_points": results, "answer": chat_content, "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>" + msg_to_display.replace('\n', '<br>')}
    
    def get_chat_history_as_text(self, history: Sequence[dict[str, str]], include_last_turn: bool=True, approx_max_tokens: int=1000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = """user:""" + "\n" + h["user"] + "\n\n" + ("""assistant:""" + "\n" + h.get("bot", "") if h.get("bot") else "") + "\n" + history_text
            if len(history_text) > approx_max_tokens*4:
                break    
        return history_text
    
    def get_messages_from_history(self, prompt_override, follow_up_questions_prompt, history: Sequence[dict[str, str]], sources: str, approx_max_tokens: int = 1000) -> list:
        '''
        Generate messages needed for chat Completion api
        '''
        messages = []
        token_count = 0
        if prompt_override is None:
            system_message = self.system_message_chat_conversation.format(injected_prompt="", follow_up_questions_prompt=follow_up_questions_prompt)
        elif prompt_override.startswith(">>>"):
            system_message = self.system_message_chat_conversation.format(injected_prompt=prompt_override[3:] + "\n", follow_up_questions_prompt=follow_up_questions_prompt)
        else:
            system_message = prompt_override.format(follow_up_questions_prompt=follow_up_questions_prompt)

        messages.append({"role":self.SYSTEM, "content": system_message})
        token_count += self.num_tokens_from_messages(messages[-1], self.chatgpt_model)
        
        # latest conversation
        user_content = history[-1]["user"] + " \nSources:" + sources
        messages.append({"role": self.USER, "content": user_content})
        token_count += token_count + self.num_tokens_from_messages(messages[-1], self.chatgpt_model)

        '''
        Enqueue in reverse order
        if limit exceeds truncate old messages 
        leaving system message behind
        Keep track of token count for each conversation
        If token count exceeds limit, break
        '''
        for h in reversed(history[:-1]):
            if h.get("bot"):
                messages.insert(1, {"role": self.ASSISTANT, "content" : h.get("bot")})
                token_count += self.num_tokens_from_messages(messages[1], self.chatgpt_model)
            messages.insert(1, {"role": self.USER, "content" : h.get("user")})
            token_count += self.num_tokens_from_messages(messages[1], self.chatgpt_model)
            if token_count > approx_max_tokens*4:
                break
        return messages
    
    def num_tokens_from_messages(self, message: dict[str,str], model: str) -> int:
        """
        Calculate the number of tokens required to encode a message.
        Args:
            message (dict): The message to encode, represented as a dictionary.
            model (str): The name of the model to use for encoding.
        Returns:
            int: The total number of tokens required to encode the message.
        Example:
            message = {'role': 'user', 'content': 'Hello, how are you?'}
            model = 'gpt-3.5-turbo'
            num_tokens_from_messages(message, model)
            output: 11
        """
        encoding = tiktoken.encoding_for_model(self.get_oai_chatmodel_tiktok(model))
        num_tokens = 0
        num_tokens += 2  # For "role" and "content" keys
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
        return num_tokens

    def get_oai_chatmodel_tiktok(self, aoaimodel: str):
        if aoaimodel == "" or aoaimodel is None:
            raise Exception("Expected AOAI chatGPT model name")
        
        return "gpt-3.5-turbo" if aoaimodel == "gpt-35-turbo" else aoaimodel