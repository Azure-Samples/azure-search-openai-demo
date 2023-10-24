from typing import Any, AsyncGenerator
import asyncio

from approaches.appresources import AppResources
from approaches.statetypes.statetype import StateType
from approaches.requestcontext import RequestContext
from approaches.utils import Utils

class StateTypePrint(StateType):
    def __init__(self, next_state, out):
        super(StateTypePrint, self).__init__(is_wait_for_user_input_before_state = False)
        self.next_state = next_state
        self.out = out
    
    async def run(self, app_resources: AppResources, session_state: Any, request_context: RequestContext) -> AsyncGenerator[dict[str, Any], None]:
        session_state["machineState"] = self.next_state

        msg_to_display = self.out.replace("\n", "<br>")

        vars = session_state["vars"]
        if not (vars is None):
            for var in vars:
                msg_to_display = msg_to_display.replace("{" + var + "}", vars[var])

        extra_info = {
            "data_points": [],
            "thoughts": f"Searched for:<br><br><br>Conversations:<br>"
            + msg_to_display,
        }

        request_context.set_response_extra_info(extra_info)

        return Utils.single_item_generator({ "choices": [{ "delta": { "content": msg_to_display } }] })