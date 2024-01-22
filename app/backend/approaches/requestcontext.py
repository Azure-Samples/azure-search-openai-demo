from typing import Any
from approaches.appresources import AppResources
from approaches.utils import Utils

class RequestContext:
    def __init__(
        self,
        app_resources: AppResources,
        session_state: Any,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        request_data: dict[str, Any],
        should_stream: bool,
        client_ip: str,
        session_user_id: str
    ):
        self.app_resources = app_resources
        self.session_state = session_state
        self.history = history
        self.overrides = overrides
        self.auth_claims = auth_claims
        self.request_data = request_data
        self.should_stream = should_stream
        self.client_ip = client_ip
        self.session_user_id = session_user_id
    
    def save_to_var(self, var_name, value):
        vars = self.session_state["vars"]
        if vars is None:
            vars = {}
            self.session_state["vars"] = vars
        vars[var_name] = value
    
    def has_var(self, var_name):
        return var_name in self.session_state["vars"]

    def get_var(self, var_name):
        return self.session_state["vars"][var_name]