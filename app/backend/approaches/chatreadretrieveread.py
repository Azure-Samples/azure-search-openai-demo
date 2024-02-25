from typing import Any, AsyncGenerator, Callable, Union

import aiohttp
from inspect import iscoroutine
from azure.monitor.events.extension import track_event
from approaches.appresources import AppResources
from approaches.approach import Approach
from approaches.flow.flow import States, FirstState
from approaches.localization.strings import get_string_by_key
from approaches.openai import OpenAI
from approaches.requestcontext import RequestContext
from approaches.utils import Utils
from approaches.flow.shared_states import ChatInputNotWait, VariableStringsId

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

        chat_input = ChatInputNotWait
        out_final = None
        while (chat_input == ChatInputNotWait):
            track_event("ChatReadRetrieveReadApproach", {"state_id": state_id, "history": history[-1]["content"], "session_user_id": request_context.session_user_id, "client_ip": request_context.client_ip, "vars": session_state["vars"]})
            if not (state.action_before is None):
                coroutine_action_before = state.action_before(request_context, history[-1]["content"])
                if iscoroutine(coroutine_action_before):
                    await coroutine_action_before
            ac = None
            for conditioned_ac in state.conditioned_actions[0]:
                if conditioned_ac.condition is None or conditioned_ac.condition(request_context, history[-1]["content"]):
                    ac = conditioned_ac
                    break
            if ac is None:
                raise Exception("Neither condition in state " + state_id + " was satisfied")

            output = None
            if not (ac.custom_action is None):
                ac = ac.custom_action(request_context)
                if iscoroutine(ac):
                    await ac
            if not (ac.output is None):
                strings_id = request_context.get_var(VariableStringsId)
                output = get_string_by_key(ac.output, strings_id, request_context)
                if isinstance(output, str):
                    output = [{"role": "assistant" , "content": output}]
                output = { "choices": [{ "delta": output }] }

            if not (output is None):
                if not (out_final is None):
                    raise Exception("Unexpected second output in state " + state_id)
                out_final = output

            state_id = ac.next_state
            if not (state_id in States):
                raise Exception("Unexpected state " + state_id)
            state = States[state_id]
            chat_input = state.chat_input

        session_state["machineState"] = state_id
        chat_input_response_item = Utils.single_item_generator(chat_input)
        if out_final is None:
            return [chat_input_response_item]
        return Utils.merge_generators([chat_input_response_item, Utils.single_item_generator(out_final)])

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
        chat_resp["choices"][0]["context"] = {"data_points": "dummy_non_null"}
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
                    "context": {"data_points": "dummy_non_null"},
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
