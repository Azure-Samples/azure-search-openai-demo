import json
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable
from typing import Any, Optional, List, Union
from dataclasses import dataclass

from openai import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
)

from approaches.approach import (
    Approach,
    DataPoints,
    ExtraInfo,
    ThoughtStep
)

class StreamingThoughtStep:
    def __init__(
            self,
            step: ThoughtStep,
            chat_completion: Optional[Union[Awaitable[ChatCompletion], Awaitable[AsyncStream[ChatCompletionChunk]]]] = None,
            role: Optional[str] = "assistant",
            data_points: Optional[DataPoints] = None,
            should_stream: bool = True):
        
        self.step = step
        self.chat_completion = chat_completion
        self.role = role
        self.data_points = data_points
        self._stream = None
        self.should_stream = should_stream
        self._steps = []
        self._step_i = -1
        self._completion = ""

    def __aiter__(self):
        return self
    
    async def start(self):
        if self._step_i < 0 and self._stream is None and self.chat_completion is not None:
            self._stream = await self.chat_completion
    
    def rewind(self):
        if not self._steps:
            raise ValueError("Cannot rewind: no steps recorded.")
        self._step_i = 0
    
    def get_completion(self) -> Optional[str]:
        return self._completion

    async def __anext__(self) -> Union[ChatCompletion, ChatCompletionChunk, DataPoints, ThoughtStep]:
        if self._step_i >= 0:
            if self._step_i < len(self._steps):
                # Return the next step in the recorded steps
                self._step_i += 1
                return self._steps[self._step_i - 1]

            raise StopAsyncIteration()

        # If there are data points, return them first to render citations
        if self.data_points is not None:
            result = self.data_points
            self.data_points = None
            self._steps.append(result)
            return result
        
        if self._stream is not None:
            if self.should_stream:
                try:
                    # Get the next chunk from the async stream
                    chunk = await self._stream.__anext__()
                    if len(chunk.choices) == 0 and chunk.usage:
                        self.step.update_token_usage(chunk.usage)
                    elif len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                        self._completion += chunk.choices[0].delta.content
                    self._steps.append(chunk)
                    return chunk
                except StopAsyncIteration:
                    # Stream is exhausted
                    self._stream = None
            else:
                # Non-Streaming Implementation: return the entire response, then the step with token usage
                result = self._stream
                self._stream = None
                self._completion = result.choices[0].message.content if result.choices else ""
                self._steps.append(result)
                return result
    
        if self.step is not None:
            result = self.step
            self.step = None
            self._steps.append(result)
            return result
    
        # No more items to yield
        raise StopAsyncIteration

@dataclass
class Reflection:
    score: Optional[int] = None
    thought_chain: Optional[str] = None
    explanation: Optional[str] = None

@dataclass
class ReflectionResponse:
    relevance: Optional[Reflection] = None
    groundedness: Optional[Reflection] = None
    correctness: Optional[Reflection] = None
    next_query: Optional[str] = None
    next_answer: Optional[str] = None

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

    def get_reflection(self, chat_completion: ChatCompletion) -> Optional[ReflectionResponse]:
        response_message = chat_completion.choices[0].message
        reflection_response = ReflectionResponse()

        print(response_message.model_dump())
        if response_message.tool_calls:
            for tool in response_message.tool_calls:
                if tool.type != "function":
                    continue
                function = tool.function
                if function.name == "reflect_answer":
                    arg = json.loads(function.arguments)
                    if relevance_reflection := arg.get("relevance"):
                        reflection_response.relevance = Reflection(
                            score=relevance_reflection.get("score"),
                            thought_chain=relevance_reflection.get("thoughtChain"),
                            explanation=relevance_reflection.get("explanation")
                        )
                    if groundedness_reflection := arg.get("groundedness"):
                        reflection_response.groundedness = Reflection(
                            score=groundedness_reflection.get("score"),
                            thought_chain=groundedness_reflection.get("thoughtChain"),
                            explanation=groundedness_reflection.get("explanation")
                        )
                    if correctness_reflection := arg.get("correctness"):
                        reflection_response.correctness = Reflection(
                            score=correctness_reflection.get("score"),
                            thought_chain=correctness_reflection.get("thoughtChain"),
                            explanation=correctness_reflection.get("explanation")
                        )
                if function.name == "search_index":
                    arg = json.loads(function.arguments)
                    reflection_response.next_query = arg.get("query")
                if function.name == "rewrite_answer":
                    arg = json.loads(function.arguments)
                    reflection_response.next_answer = arg.get("answer")

        return reflection_response

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
        thoughts = self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=False
        )
        content = None
        role = None
        extra_info = ExtraInfo()
        async for thought in thoughts:
            await thought.start()
            async for chunk in thought:
                if isinstance(chunk, ChatCompletion):
                    content = chunk.choices[0].message.content
                    role = chunk.choices[0].message.role
                elif isinstance(chunk, ThoughtStep):
                   extra_info.thoughts.append(chunk)
                elif isinstance(chunk, DataPoints):
                    extra_info.data_points = chunk

        if overrides.get("suggest_followup_questions"):
            content, followup_questions = self.extract_followup_questions(content)
            followup_questions = followup_questions
        return {
            "message": {"content": content, "role": role},
            "context": extra_info,
            "session_state": session_state,
        }

    async def run_with_streaming(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        session_state: Any = None,
    ) -> AsyncGenerator[dict, None]:
        thoughts = self.run_until_final_call(
            messages, overrides, auth_claims, should_stream=True
        )
        extra_info = ExtraInfo()

        yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}
        followup_questions_started = False
        followup_content = ""
        async for thought in thoughts:
            await thought.start()
            async for chunk in thought:
                if isinstance(chunk, ChatCompletionChunk):
                    if chunk.choices:
                        content = chunk.choices[0].delta.content
                        role = chunk.choices[0].delta.role
                        content = content or ""  # content may either not exist in delta, or explicitly be None
                        completion = { "delta": {"content": content, "role": role} }
                        if overrides.get("suggest_followup_questions") and "<<" in content:
                            # if event contains << and not >>, it is start of follow-up question, truncate
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
                elif isinstance(chunk, ThoughtStep):
                    extra_info.thoughts.append(chunk)
                    yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}
                elif isinstance(chunk, DataPoints):
                    extra_info.data_points = chunk
                    yield {"delta": {"role": "assistant"}, "context": extra_info, "session_state": session_state}

            if followup_content:
                _, followup_questions = self.extract_followup_questions(followup_content)
                extra_info.followup_questions = followup_questions
                yield {
                    "delta": {"role": "assistant"},
                    "context": extra_info,
                }

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
