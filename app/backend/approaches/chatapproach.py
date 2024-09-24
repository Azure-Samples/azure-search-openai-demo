import json
import re
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from approaches.approach import Approach


class ChatApproach(Approach, ABC):
    query_prompt_few_shots: list[ChatCompletionMessageParam] = [
        {"role": "user", "content": "What funding is available to start a new business in New Zealand?"},
        {
            "role": "assistant",
            "content": "There are a lot of funding options available to start a new business in New Zealand. Some of the options include grants, loans, and equity investment. Can you tell me more about the type of funding you're looking for?",
        },
        {"role": "user", "content": "Who can help me with R&D funding in New Zealand?"},
        {
            "role": "assistant",
            "content": "There are several agencies who can help you find R&D funding in New Zealand, such as Callaghan Innovation and NZ Trade and Enterprise. Can you tell me more about the type of R&D funding you're looking for?",
        },
        {"role": "user", "content": "Tell me more about this assistant."},
        {
            "role": "assistant",
            "content": "I'm GovGPT, your New Zealand Government chat companion here to help you navigate and understand government services for small businesses. Whether you're starting out or looking to grow, I'm here to provide you with information and guide you to the resources you need. Feel free to ask me anything about business support in New Zealand! You can find more information about me on Callaghan Innovation's website, at https://www.callaghaninnovation.govt.nz/.",
        },
    ]
    NO_RESPONSE = "0"

    follow_up_questions_prompt_content = """- Generate 3 concise follow-up questions that the user might ask next based on the conversation so far.
- Use the system message to ensure your tone and style are consistent with the previous interactions.
- Enclose each follow-up question in double angle brackets. For example:
  <<Which agency can help me with that?>>
  <<Are there specific requirements?>>
  <<Where can I find more information?>>
- Do not repeat questions that have already been asked.
- Ensure the last question ends with ">>".
"""

    query_prompt_template = """Below is the conversation history and a new question from the user that needs to be answered by searching a knowledge base.
You have access to an Azure AI Search index containing thousands of documents.
Your task is to generate a search query based on the conversation and the new question, following these guidelines:
1. Content Exclusions:
   - Do not include cited source filenames or document names (e.g., info.txt, doc.pdf) in the search query terms.
   - Do not include any text enclosed within square brackets [ ] or double angle brackets << >> in the search query terms.
2. Formatting:
   - Do not include any special characters such as + in the search query terms.
3. Language Translation:
   - If the question is not in English, translate it to English before generating the search query.
4. Unable to Generate Query:
   - If you cannot generate a search query, return only the number 0.
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
