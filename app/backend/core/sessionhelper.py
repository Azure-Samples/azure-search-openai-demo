import uuid


def create_session_id(config_chat_history_browser_enabled: bool) -> str | None:
    if config_chat_history_browser_enabled:
        return str(uuid.uuid4())
    return None
