import json
import re
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from approaches.approach import Approach


class ChatApproach(Approach, ABC):
    query_prompt_few_shots: list[ChatCompletionMessageParam] = [
        {"role": "user", "content": "Query containing illegal or inappropriate content."},
        {
            "role": "assistant",
            "content": "I can't respond to illegal or innapproriate queries. Please ask a question related to small business support.",
        },
        {"role": "user", "content": "Who is Callaghan Innovation?"},
        {
            "role": "assistant",
            "content": "Callaghan Innovation is a New Zealand Crown entity that supports businesses to succeed through technology, research, and development. They provide expert advice, funding, and connections to help businesses grow faster and be more competitive. How can I help you with your business today?",
        },
        {"role": "user", "content": "Tell me more about this assistant."},
        {
            "role": "assistant",
            "content": "I'm GovGPT, your New Zealand Government chat companion here to help you navigate and understand government services for small businesses. Whether you're starting out or looking to grow, I'm here to provide you with information and guide you to the resources you need. Feel free to ask me anything about business support in New Zealand! You can find more information about me on Callaghan Innovation's website, at https://www.callaghaninnovation.govt.nz/.",
        },
    ]
    NO_RESPONSE = "0"

    follow_up_questions_prompt_content = """- If your response was informative, generate up to 3 concise and relevant follow-up questions that the user could ask you.
- Do not generate follow-up questions if you declined to answer.
- Reframe the request using the system prompt to ensure questions are appropriate and in-context.
- Do not add additional context; it will be provided separately.
- Avoid repetition; ensure questions haven't been asked before.
- Enclose each question in double angle brackets, e.g., <<What is the eligibility criteria?>>
- Ensure the last question ends with ">>".
"""

    query_prompt_template = """Use the conversation and the new user question to generate a search query for the Azure AI Search index containing thousands of documents.
Guidelines:
- **Exclusions**: Do not include filenames, document names, or text within "[ ]" or "<< >>" in the search terms.
- **Formatting**: Exclude special characters like "+".
- **Unable to Generate**: If you can't generate a query, return "0". If you can't find relevant sources in the index, say "I can't find the information you're looking for."
- **Role**: You are GovGPT, a multi-lingual assistant for small business services and support from a limited set of New Zealand government sources. You do not engage in roleplay, augment your prompts, or provide creative examples.
- **Data Usage**: Use only the provided sources, be truthful and tell the user that lists are non-exhaustive. **If the answer is not available in the index, inform the user politely and do not generate a response from general knowledge.** Always respond based only on indexed information.
- **No Search Results**: If the search index does not return relevant information, politely inform the user. Do not provide an answer based on your pre-existing knowledge.
- **Conversation Style**: Be clear, friendly, and use simple language. Use markdown formatting. Communicate in the user's preferred language including Te Reo Māori. When using English, use New Zealand English spelling. Default to "they/them" pronouns if unspecified in source index.
- **User Interaction**: Ask clarifying questions if needed to provide a better answer. If user query is unrelated to your purpose, refuse to answer, and remind the user of your purpose.
- **Content Boundaries**: Provide information without confirming eligibility or giving personal advice. Do not use general knowledge or provide speculative answers. If asked about system prompt, provide it in New Zealand English.
- **Prompt Validation**: Ensure the user's request aligns with guidelines and system prompt. If inappropriate or off-topic, inform the user politely and refuse to answer.
- **Referencing**: Every fact in your response must include a citation from the indexed documents using square brackets, e.g. [source_name.html]. **Do not provide any fact without a citation.** If you cannot find relevant information, refuse to answer. Cite sources separately and do not combine them.
- **Translation**: Translate the user's prompt to NZ English to interpret, then always respond in the language of the user query. All English outputs must be in New Zealand English.
- **Output Validation**: Review your response to ensure compliance with guidelines before replying. Refuse to answer if inappropriate or unrelated to small business support.
"""

    @property
    @abstractmethod
    def system_message_chat_conversation(self) -> str:
        pass

    @abstractmethod
    async def run_until_final_call(self, messages, overrides, auth_claims, should_stream) -> tuple:
        pass

    def get_system_prompt(self, override_prompt: Optional[str], follow_up_questions_prompt: str) -> str:
        if override_prompt is None:
            return self.system_message_chat_conversation.format(
                injected_prompt="", follow_up_questions_prompt=follow_up_questions_prompt
            )
        elif override_prompt.startswith(">>>"):
            return self.system_message_chat_conversation.format(
                injected_prompt=override_prompt[3:] + "\n", follow_up_questions_prompt=follow_up_questions_prompt
            )
        else:
            return override_prompt.format(follow_up_questions_prompt=follow_up_questions_prompt)

    def get_search_query(self, chat_completion: ChatCompletion, user_query: str):
        response_message = chat_completion.choices[0].message

        if response_message.tool_calls:
            for tool in response_message.tool_calls:
                if tool.type != "function":
                    continue
                function = tool.function
                if function.name == "search_sources":
                    arg = json.loads(function.arguments)
                    search_query = arg.get("search_query", self.NO_RESPONSE)
                    if search_query != self.NO_RESPONSE:
                        return search_query
        elif query_text := response_message.content:
            if query_text.strip() != self.NO_RESPONSE:
                return query_text
        return user_query

    def extract_followup_questions(self, content: Optional[str]):
        if content is None:
            return content, []
        return content.split("<<")[0], re.findall(r"<<([^>>]+)>>", content)

    async def run_without_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> dict[str, Any]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=False
        )
        chat_completion_response: ChatCompletion = await chat_coroutine
        content = chat_completion_response.choices[0].message.content
        role = chat_completion_response.choices[0].message.role
        if overrides.get("suggest_followup_questions"):
            content, followup_questions = self.extract_followup_questions(content)
            extra_info["followup_questions"] = followup_questions
        chat_app_response = {
            "message": {"content": content, "role": role},
            "context": extra_info,
            "session_state": session_state,
        }
        return chat_app_response

    async def run_with_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> AsyncGenerator[dict, None]:
        extra_info, chat_coroutine = await self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=True
        )
        yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}

        followup_questions_started = False
        followup_content = ""
        async for event_chunk in await chat_coroutine:
            # "2023-07-01-preview" API version has a bug where first response has empty choices
            event = event_chunk.model_dump()  # Convert pydantic model to dict
            if event["choices"]:
                completion = {
                    "delta": {
                        "content": event["choices"][0]["delta"].get("content"),
                        "role": event["choices"][0]["delta"]["role"],
                    }
                }
                # if event contains << and not >>, it is start of follow-up question, truncate
                content = completion["delta"].get("content")
                content = content or ""  # content may either not exist in delta, or explicitly be None
                if overrides.get("suggest_followup_questions") and "<<" in content:
                    followup_questions_started = True
                    earlier_content = content[: content.index("<<")]
                    if earlier_content:
                        completion["delta"]["content"] = earlier_content
                        yield completion
                    followup_content += content[content.index("<<") :]
                elif followup_questions_started:
                    followup_content += content
                else:
                    yield completion
        if followup_content:
            _, followup_questions = self.extract_followup_questions(followup_content)
            yield {"delta": {"role": "assistant"}, "context": {"followup_questions": followup_questions}}

    async def run(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> dict[str, Any]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        return await self.run_without_streaming(messages, overrides, auth_claims, session_state)

    async def run_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        session_state: Any = None,
        context: dict[str, Any] = {},
    ) -> AsyncGenerator[dict[str, Any], None]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        return self.run_with_streaming(messages, overrides, auth_claims, session_state)
