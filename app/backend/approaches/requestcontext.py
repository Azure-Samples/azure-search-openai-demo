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
        self.extra_info = None
        self.client_ip = client_ip
        self.session_user_id = session_user_id
    
    def set_response_extra_info(self, extra_info: dict[str, str]):
        if self.has_extra_info():
            raise Exception("Unexpected two results")
        self.extra_info = extra_info

    def has_extra_info(self):
        return not (self.extra_info is None)
    
    def write_chat_message(self, msg_to_display):
        return self.write_roled_chat_message([{ "content": msg_to_display, "role": "assistant" }], msg_to_display)
    
    def write_roled_chat_message(self, roled_parts, extra_info_string = None):
        extra_info = {
            "data_points": [],
            "thoughts": f"Searched for:<br><br><br>Conversations:<br>" + ("styled_text" if extra_info_string is None else extra_info_string),
        }

        self.set_response_extra_info(extra_info)

        return Utils.single_item_generator({ "choices": [{ "delta": roled_parts }] })
    
    def set_next_state(self, next_state):
        self.session_state["machineState"] = next_state

    def save_to_var(self, var_name, value):
        vars = self.session_state["vars"]
        if vars is None:
            vars = {}
            self.session_state["vars"] = vars
        vars[var_name] = value

    def get_var(self, var_name):
        return self.session_state["vars"][var_name]