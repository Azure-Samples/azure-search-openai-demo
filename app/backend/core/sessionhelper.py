import uuid
from typing import Union


def create_session_id(config_chat_history_browser_enabled: bool) -> Union[str, None]:
    if config_chat_history_browser_enabled:
        return str(uuid.uuid4())
    return None
