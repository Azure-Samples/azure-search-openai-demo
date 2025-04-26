import json
from typing import Any, Awaitable, List, Optional, Union, cast

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorQuery
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

from approaches.approach import DataPoints, ExtraInfo, ThoughtStep
from approaches.chatapproach import ChatApproach
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper


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
        openai_client: AsyncOpenAI,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        embedding_dimensions: int,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        prompt_manager: PromptManager,
        reasoning_effort: Optional[str] = None,
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.prompt_manager = prompt_manager
        self.query_rewrite_prompt = self.prompt_manager.load_prompt("chat_query_rewrite.prompty")
        self.query_rewrite_tools = self.prompt_manager.load_tools("chat_query_rewrite_tools.json")
        self.answer_prompt = self.prompt_manager.load_prompt("chat_answer_question.prompty")
        self.reasoning_effort = reasoning_effort
        self.include_token_usage = True

    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[ExtraInfo, Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]]]:
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        use_query_rewriting = True if overrides.get("query_rewriting") else False
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        filter = self.build_filter(overrides, auth_claims)

        original_user_query = messages[-1]["content"]
        if not isinstance(original_user_query, str):
            raise ValueError("The most recent message content must be a string.")

        reasoning_model_support = self.GPT_REASONING_MODELS.get(self.chatgpt_model)
        if reasoning_model_support and (not reasoning_model_support.streaming and should_stream):
            raise Exception(
                f"{self.chatgpt_model} does not support streaming. Please use a different model or disable streaming."
            )

        query_messages = self.prompt_manager.render_prompt(
            self.query_rewrite_prompt,
            {
                "user_query": original_user_query,
                "past_messages": messages[:-1],
                "user_email": auth_claims.get("email", ""),
            },
        )
        tools: List[ChatCompletionToolParam] = self.query_rewrite_tools

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question

        chat_completion = cast(
            ChatCompletion,
            await self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages=query_messages,
                overrides=overrides,
                response_token_limit=self.get_response_token_limit(
                    self.chatgpt_model, 100
                ),  # Setting too low risks malformed JSON, setting too high may affect performance
                temperature=0.0,  # Minimize creativity for search query generation
                tools=tools,
                reasoning_effort="low",  # Minimize reasoning for search query generation
            ),
        )

        tool_type = self.get_tool_type(chat_completion)

        # If the model chose to send an email, handle that separately
        if tool_type == "send_email":
            email_data = self.get_email_data(chat_completion)
            # Format the chat history as HTML for the email
            chat_history_html = self.format_chat_history_as_html(messages[:-1])
            # Add the original query at the end
            chat_history_html += f"<p><strong>User:</strong> {original_user_query}</p>"

            # Send the email via Graph API
            if "oid" in auth_claims:
                await self.send_chat_history_email(
                    auth_claims,
                    email_data["to_email"],
                    email_data["subject"],
                    email_data["introduction"],
                    chat_history_html,
                )

                # Set up a response indicating email was sent
                extra_info = ExtraInfo(
                    DataPoints(text=""),
                    thoughts=[ThoughtStep("Email sent", "Email with chat history sent to user", {})],
                )

                # Create a response that indicates the email was sent
                response_message = f"I've sent an email with our conversation history to your registered email address with the subject: '{email_data['subject']}'."

                # Create a chat completion object manually as we're not going through normal flow
                chat_coroutine = self.create_chat_completion(
                    self.chatgpt_deployment,
                    self.chatgpt_model,
                    [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant, let the user know that you've completed the requested action.",
                        },
                        {"role": "user", "content": "Send email with chat history"},
                        {"role": "assistant", "content": response_message},
                    ],
                    overrides,
                    self.get_response_token_limit(self.chatgpt_model, 300),
                    should_stream,
                )

                return (extra_info, chat_coroutine)

        # If the model chose to add a note, handle that separately
        if tool_type == "add_note":
            note_data = self.get_note_data(chat_completion)
            # Format the chat history as HTML for the OneNote page
            chat_history_html = self.format_chat_history_as_html(messages[:-1])
            # Compose the full OneNote page content
            full_content = f"<p>{note_data['intro_content']}</p>" + chat_history_html
            # Create the OneNote page via Graph API
            if "oid" in auth_claims:
                note_response = await self.auth_helper.create_onenote_page(
                    graph_resource_access_token=auth_claims.get("graph_resource_access_token"),
                    title=note_data["title"],
                    content_html=full_content,
                )
                extra_info = ExtraInfo(
                    DataPoints(text=""),
                    thoughts=[ThoughtStep("OneNote page created", "OneNote page with chat history created", {})],
                )
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant, let the user know that you've completed the requested action.",
                    },
                    {"role": "user", "content": original_user_query},
                    {"role": "assistant", "tool_calls": chat_completion.choices[0].message.tool_calls},
                    {
                        "role": "tool",
                        "tool_call_id": chat_completion.choices[0].message.tool_calls[0].id,
                        "content": json.dumps(note_response),
                    },
                ]
                chat_coroutine = self.create_chat_completion(
                    self.chatgpt_deployment,
                    self.chatgpt_model,
                    messages,
                    overrides,
                    self.get_response_token_limit(self.chatgpt_model, 300),
                    should_stream,
                )
                return (extra_info, chat_coroutine)

        # Extract search query if it's a search request
        query_text = self.get_search_query(chat_completion, original_user_query, tool_type)

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
            use_query_rewriting,
        )

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        text_sources = self.get_sources_content(results, use_semantic_captions, use_image_citation=False)
        messages = self.prompt_manager.render_prompt(
            self.answer_prompt,
            self.get_system_prompt_variables(overrides.get("prompt_template"))
            | {
                "include_follow_up_questions": bool(overrides.get("suggest_followup_questions")),
                "past_messages": messages[:-1],
                "user_query": original_user_query,
                "text_sources": text_sources,
            },
        )

        extra_info = ExtraInfo(
            DataPoints(text=text_sources),
            thoughts=[
                self.format_thought_step_for_chatcompletion(
                    title="Prompt to generate search query",
                    messages=query_messages,
                    overrides=overrides,
                    model=self.chatgpt_model,
                    deployment=self.chatgpt_deployment,
                    usage=chat_completion.usage,
                    reasoning_effort="low",
                ),
                ThoughtStep(
                    "Search using generated search query",
                    query_text,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "use_query_rewriting": use_query_rewriting,
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
                self.format_thought_step_for_chatcompletion(
                    title="Prompt to generate answer",
                    messages=messages,
                    overrides=overrides,
                    model=self.chatgpt_model,
                    deployment=self.chatgpt_deployment,
                    usage=None,
                ),
            ],
        )

        chat_coroutine = cast(
            Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]],
            self.create_chat_completion(
                self.chatgpt_deployment,
                self.chatgpt_model,
                messages,
                overrides,
                self.get_response_token_limit(self.chatgpt_model, 1024),
                should_stream,
            ),
        )
        return (extra_info, chat_coroutine)

    def get_search_query(self, chat_completion: ChatCompletion, original_user_query: str, tool_type: str) -> str:
        """Extract the search query from the chat completion"""
        if tool_type != "search_sources":
            return original_user_query

        if not chat_completion.choices or not chat_completion.choices[0].message:
            return original_user_query

        message = chat_completion.choices[0].message

        if not message.tool_calls:
            # If no tool calls but content exists, try to extract query from content
            if message.content and message.content.strip() != "0":
                return message.content
            return original_user_query

        # For each tool call, check if it's a search_sources call and extract the query
        for tool_call in message.tool_calls:
            if tool_call.function.name == "search_sources":
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    if "search_query" in arguments:
                        return arguments["search_query"]
                except (json.JSONDecodeError, KeyError):
                    pass

        return original_user_query

    def get_email_data(self, chat_completion: ChatCompletion) -> dict:
        """Extract email data from a send_email tool call"""
        message = chat_completion.choices[0].message

        for tool_call in message.tool_calls:
            if tool_call.function.name == "send_email":
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    return {
                        "subject": arguments.get("subject", "Chat History"),
                        "to_email": arguments.get("to_email", ""),
                        "introduction": arguments.get("introduction", "Here is your requested chat history:"),
                    }
                except (json.JSONDecodeError, KeyError):
                    # Return defaults if there's an error parsing the arguments
                    return {
                        "subject": "Chat History",
                        "to_email": "",
                        "introduction": "Here is your requested chat history:",
                    }

        # Fallback defaults
        return {"subject": "Chat History", "to_email": "", "introduction": "Here is your requested chat history:"}

    def get_note_data(self, chat_completion: ChatCompletion) -> dict:
        """Extract note data from an add_note tool call"""
        message = chat_completion.choices[0].message
        for tool_call in message.tool_calls:
            if tool_call.function.name == "add_note":
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    title = arguments.get("title")
                    intro_content = arguments.get("intro_content")
                except (json.JSONDecodeError, KeyError):
                    pass
        return {
            "title": title if title else "Chat History",
            "intro_content": intro_content if intro_content else "Here is the chat history:",
        }

    def format_chat_history_as_html(self, messages: list[ChatCompletionMessageParam]) -> str:
        """Format the chat history as HTML for email"""
        html = ""
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            if not content or not isinstance(content, str):
                continue

            if role == "user":
                html += f"<p><strong>User:</strong> {content}</p>"
            elif role == "assistant":
                html += f"<p><strong>Assistant:</strong> {content}</p>"
            elif role == "system":
                # Usually we don't include system messages in the chat history for users
                pass

        return html

    async def send_chat_history_email(
        self, auth_claims: dict, to_email: str, subject: str, introduction: str, chat_history_html: str
    ) -> dict:
        """Send the chat history as an email to the user"""
        # Create the full email content with the introduction and chat history
        full_content = f"{introduction}\n\n{chat_history_html}"
        print(f"Sending email to {to_email} with subject: {subject}")
        # Call send_mail with all required parameters
        return await self.auth_helper.send_mail(
            graph_resource_access_token=auth_claims.get("graph_resource_access_token"),
            to_recipients=[to_email],
            subject=subject,
            content=full_content,
            content_type="HTML",
        )

    def get_tool_type(self, chat_completion: ChatCompletion) -> str:
        """Determine the type of tool call in the chat completion"""
        if not chat_completion.choices or not chat_completion.choices[0].message:
            return ""

        message = chat_completion.choices[0].message
        if not message.tool_calls:
            return ""

        for tool_call in message.tool_calls:
            return tool_call.function.name

        return ""
