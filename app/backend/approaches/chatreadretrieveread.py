from typing import Any, AsyncGenerator, Union

import aiohttp
from inspect import iscoroutine

from approaches.appresources import AppResources
from approaches.approach import Approach
from approaches.flow.flow import States, FirstState
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext
from approaches.utils import Utils

class ChatReadRetrieveReadApproach(Approach):
    def __init__(self, app_resources: AppResources):
        self.app_resources = app_resources

    async def run_until_final_call(
        self,
        session_state: Any,
        request_context: RequestContext,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> AsyncGenerator[dict, None]:
        if not ("machineState" in session_state):
            raise Exception("No machineState in session_state")
        state_id = session_state["machineState"]
        if not (state_id in States):
            raise Exception("Unexpected state " + state_id)
        state = States[state_id]

        event_generators = []
        is_wait_for_user_input_before_state = False
        while (not is_wait_for_user_input_before_state):
            chat_coroutine = state.run(request_context)
            if not (chat_coroutine is None):
                if iscoroutine(chat_coroutine):
                    chat_coroutine = await chat_coroutine
            if not (chat_coroutine is None):
                event_generators.append(chat_coroutine)

            state_id = session_state["machineState"]
            if not (state_id in States):
                raise Exception("Unexpected state " + state_id)
            state = States[state_id]
            is_wait_for_user_input_before_state = state.is_wait_for_user_input_before_state

        # Return after aggregation, so request_context.extra_info has already been set
        return Utils.merge_generators(event_generators)

    async def run_without_streaming(
        self,
        session_state: Any,
        request_context: RequestContext,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
    ) -> dict[str, Any]:
        chat_coroutine = await self.run_until_final_call(
            session_state, request_context, history, overrides, auth_claims, should_stream=False
        )
        chat_resp = dict(await chat_coroutine)
        chat_resp["choices"][0]["context"] = request_context.extra_info
        chat_resp["choices"][0]["session_state"] = session_state
        return chat_resp

    async def run_with_streaming(
        self,
        session_state: Any,
        request_context: RequestContext,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
    ) -> AsyncGenerator[dict, None]:
        chat_coroutine = await self.run_until_final_call(
            session_state, request_context, history, overrides, auth_claims, should_stream=True
        )

        yield {
            "choices": [
                {
                    "delta": {"role": OpenAI.ASSISTANT},
                    "context": request_context.extra_info,
                    "session_state": session_state,
                    "finish_reason": None,
                    "index": 0,
                }
            ],
            "object": "chat.completion.chunk",
        }

        async for event in chat_coroutine:
            yield event

    async def run(
        self, messages: list[dict], stream: bool = False, session_state: Any = None, context: dict[str, Any] = {}, request_data: dict[str, Any] = {}
    ) -> Union[dict[str, Any], AsyncGenerator[dict[str, Any], None]]:
        overrides = context.get("overrides", {})
        auth_claims = context.get("auth_claims", {})
        if session_state is None:
            session_state = { "machineState": FirstState, "vars": {} }
        request_context = RequestContext(self.app_resources, session_state, messages, overrides, auth_claims, request_data, stream, context["client_ip"], context["session_user_id"])
        if stream is False:
            # Workaround for: https://github.com/openai/openai-python/issues/371
            async with aiohttp.ClientSession() as s:
                openai.aiosession.set(s)
                response = await self.run_without_streaming(session_state, request_context, messages, overrides, auth_claims)
            return response
        else:
            return self.run_with_streaming(session_state, request_context, messages, overrides, auth_claims)
