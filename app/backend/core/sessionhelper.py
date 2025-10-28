import uuid
from typing import Optional


def create_session_id(
    config_chat_history_cosmos_enabled: bool, config_chat_history_browser_enabled: bool
) -> Optional[str]:
    if config_chat_history_cosmos_enabled:
        return str(uuid.uuid4())
    if config_chat_history_browser_enabled:
        return str(uuid.uuid4())
    return None
