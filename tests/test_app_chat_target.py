import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from pyrit.common import net_utility
from pyrit.models import ChatMessage, PromptRequestResponse

from evaluation.app_chat_target import AppChatTarget

skip_if_python_incompatible = pytest.mark.skipif(
    sys.version_info < (3, 10) or sys.version_info >= (3, 12),
    reason="requires Python 3.10 and 3.11, due to PyRIT dependency",
)


@pytest.fixture
def chat_target():
    return AppChatTarget(endpoint_uri="http://dummy-endpoint.com", target_parameters={"param1": "value1"})


@pytest.fixture
def prompt_request_response():
    message = ChatMessage(role="user", content="Hello, how are you?")
    request_pieces = [MagicMock()]
    request_pieces[0].to_chat_message = MagicMock(return_value=message)
    request_pieces[0].converted_value_data_type = "text"
    return PromptRequestResponse(request_pieces=request_pieces)


@pytest.mark.asyncio
@skip_if_python_incompatible
async def test_complete_chat_async(chat_target):
    chat_target._get_headers = MagicMock(return_value={})
    chat_target._construct_http_body = MagicMock(return_value={})

    net_utility.make_request_and_raise_if_error_async = AsyncMock()
    net_utility.make_request_and_raise_if_error_async.return_value.json = MagicMock(
        return_value={"message": {"content": "Test response"}}
    )

    messages = [ChatMessage(role="user", content="Test message")]

    response = await chat_target._complete_chat_async(messages=messages, target_parameters={})

    assert response == "Test response"


@skip_if_python_incompatible
def test_construct_http_body(chat_target):
    messages = [ChatMessage(role="user", content="Test message")]
    chat_target.chat_message_normalizer = MagicMock()
    chat_target.chat_message_normalizer.normalize = MagicMock(return_value=messages)

    body = chat_target._construct_http_body(messages, {"param1": "value1"})

    assert "messages" in body
    assert "context" in body
    assert body["context"] == {"param1": "value1"}
    assert body["messages"][0]["content"] == "Test message"


@skip_if_python_incompatible
def test_get_headers(chat_target):
    headers = chat_target._get_headers()
    assert headers == {"Content-Type": "application/json"}


@skip_if_python_incompatible
def test_validate_request(chat_target, prompt_request_response):
    chat_target._validate_request(prompt_request=prompt_request_response)

    prompt_request_response.request_pieces[0].converted_value_data_type = "non-text"
    with pytest.raises(ValueError, match="This target only supports text prompt input."):
        chat_target._validate_request(prompt_request=prompt_request_response)

    prompt_request_response.request_pieces = []
    with pytest.raises(ValueError, match="This target only supports a single prompt request piece."):
        chat_target._validate_request(prompt_request=prompt_request_response)
