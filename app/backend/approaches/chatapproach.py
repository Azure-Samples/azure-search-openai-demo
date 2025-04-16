import json
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable
from typing import Any, Optional, List, Union

from openai import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)

from approaches.approach import (
    Approach,
    ThoughtStep
)

class StreamingThoughtStep:
    def __init__(self, step: ThoughtStep, chat_completion: Optional[Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]]] = None, role: Optional[str] = "assistant"):
        self.step = step
        self.chat_completion = chat_completion
        self.role = role
        self._stream = None
        self._is_streaming = None
    
    def has_content(self) -> bool:
        return self.chat_completion is not None

    def __aiter__(self):
        return self
    
    async def start(self):
        if self._stream is None and self.chat_completion is not None:
            self._stream = await self.chat_completion
            self._is_streaming = True

    async def __anext__(self) -> Union[ChatCompletion, ChatCompletionChunk, ThoughtStep]:
        if self._is_streaming:
            # Streaming Implementation: yield each chunk, then the step with token usage
            if self._stream is None:
                raise StopAsyncIteration

            try:
                # Get the next chunk from the async stream
                chunk = await self._stream.__anext__()
                if len(chunk.choices) == 0 and chunk.usage:
                    self.step.update_token_usage(chunk.usage)
                return chunk
            except StopAsyncIteration:
                # If the stream is exhausted, yield the step with token usage
                self._stream = None
                return self.step
        
        # Non-Streaming Implementation: return the entire response, then the step with token usage
        if self._stream is None:
            if self.step is None:
                raise StopAsyncIteration
            
            result = self.step
            self.step = None
            return result

        result = self._stream
        self._stream = None
        return result

class ChatApproach(Approach, ABC):

    NO_RESPONSE = "0"

    @abstractmethod
    async def run_until_final_call(
        self, messages, overrides, auth_claims, should_stream
    ) -> AsyncGenerator[StreamingThoughtStep, None]:
        pass

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

    def extract_followup_questions(self, content: Optional[str]) -> Optional[List[str]]:
        if content is None:
            return content, []
        return content.split("<<")[0], re.findall(r"<<([^>>]+)>>", content)

    async def run_without_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        thoughts = self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=False
        )
        async for thought in thoughts:
            content = None
            role = None
            thought_step = None
            followup_questions = None
            await thought.start()
            async for chunk in thought:
                if isinstance(chunk, ChatCompletion):
                    content = chunk.choices[0].message.content
                    role = chunk.choices[0].message.role
                elif isinstance(chunk, ThoughtStep):
                   thought_step = chunk

            if overrides.get("suggest_followup_questions"):
                content, followup_questions = self.extract_followup_questions(content)
                followup_questions = followup_questions

            yield {
                "message": {"content": content, "role": role},
                "context": { "thought": thought_step, "followup_questions": followup_questions },
                "session_state": session_state,
            }

    async def run_with_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        thoughts = self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=True
        )
        async for thought in thoughts:
            yield { "delta": { "role": thought.role }, "has_content": thought.has_content() }

            followup_questions_started = False
            followup_content = ""
            thought_step = None
            await thought.start()
            async for event in thought:
                if isinstance(event, ChatCompletionChunk):
                    if event.choices:
                        completion = {
                            "delta": {
                                "content": event.choices[0].delta.content,
                                "role": event.choices[0].delta.role
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
                elif isinstance(event, ThoughtStep):
                    thought_step = event

            followup_questions = None
            if followup_content:
                _, followup_questions = self.extract_followup_questions(followup_content)
            yield {"delta": {"role": thought.role, "finish_reason": "stop" }, "context": { "thought": thought_step, "followup_questions": followup_questions }, "session_state": session_state }

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
