from typing import Any, AsyncGenerator

from approaches.appresources import AppResources
from approaches.statetypes.statetype import StateType
from approaches.requestcontext import RequestContext
from approaches.utils import Utils

class StateTypeSaveInputToVar(StateType):
    def __init__(self, next_state, var):
        super(StateTypeSaveInputToVar, self).__init__(is_wait_for_user_input_before_state = True)
        self.next_state = next_state
        self.var = var
    
    async def run(self, app_resources: AppResources, session_state: Any, request_context: RequestContext) -> AsyncGenerator[dict[str, Any], None]:
        session_state["machineState"] = self.next_state
        
        vars = session_state["vars"]
        if vars is None:
            vars = {}
            session_state["vars"] = vars
        vars[self.var] = request_context.history[-1]["content"]
        
        return None