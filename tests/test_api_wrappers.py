from unittest import mock

import pytest

from api_wrappers import HuggingFaceClient


@pytest.fixture
def mock_client():
    with mock.patch("api_wrappers.hugging_face.AsyncInferenceClient", autospec=True) as MockAsyncInferenceClient:
        mock_client_instance = MockAsyncInferenceClient.return_value
        mock_client_instance.chat_completion = mock.AsyncMock()

        client = HuggingFaceClient(model="test-model")
        yield client, mock_client_instance


@pytest.mark.asyncio
async def test_chat_completion(mock_client):
    client, mock_async_inference_client = mock_client
    messages = [{"role": "user", "content": "Hello, how are you?"}]
    expected_output = {"response": "I'm a test AI model!"}

    # Set up the mock to return the expected output
    mock_async_inference_client.chat_completion.return_value = expected_output

    result = await client.chat_completion(messages=messages)
    assert result == expected_output

    mock_async_inference_client.chat_completion.assert_awaited_once_with(
        messages=messages,
        model=None,
        stream=False,
        frequency_penalty=None,
        logit_bias=None,
        logprobs=None,
        max_tokens=None,
        n=None,
        presence_penalty=None,
        seed=None,
        stop=None,
        temperature=None,
        tool_choice=None,
        tool_prompt=None,
        tools=None,
        top_logprobs=None,
        top_p=None,
    )


def test_format_message():
    client = HuggingFaceClient()
    messages = [
        {"role": "system", "content": "system instructions"},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I am good, thank you."},
    ]
    expected_output = [
        {"role": "user", "content": "system instructions\n\nHello, how are you?"},
        {"role": "assistant", "content": "I am good, thank you."},
    ]
    formatted_messages = client.format_message(messages)

    assert formatted_messages == expected_output


def test_format_message_raises_error_on_same_role():
    client = HuggingFaceClient()
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "user", "content": "How's the weather?"},
    ]

    with pytest.raises(ValueError, match="Messages must alternate roles between user and assistant."):
        client.format_message(messages)


def test_format_message_raises_error_if_first_message_not_user():
    client = HuggingFaceClient()
    messages = [
        {"role": "assistant", "content": "I am good, thank you."},
        {"role": "user", "content": "How's the weather?"},
    ]

    with pytest.raises(ValueError, match="The first message must be from the user."):
        client.format_message(messages)


def test_extract_content_as_string():
    client = HuggingFaceClient()

    content_str = "Hello, world!"
    assert client._extract_content_as_string(content_str) == content_str

    content_text = {"type": "text", "text": "Hello, text!"}
    assert client._extract_content_as_string(content_text) == "Hello, text!"

    content_image = {"type": "image_url", "image_url": {"url": "http://example.com/image.png"}}
    assert client._extract_content_as_string(content_image) == "http://example.com/image.png"
