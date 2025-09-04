import json
import logging

import aiohttp
import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from prepdocslib.mediadescriber import (
    ContentUnderstandingDescriber,
    MultimodalModelDescriber,
)

from .mocks import MockAzureCredential, MockResponse


@pytest.mark.asyncio
async def test_contentunderstanding_analyze(monkeypatch, caplog):

    def mock_post(*args, **kwargs):
        if kwargs.get("url").find("badanalyzer") > 0:
            return MockResponse(
                status=200,
                headers={
                    "Operation-Location": "https://testcontentunderstanding.cognitiveservices.azure.com/contentunderstanding/analyzers/badanalyzer/operations/7f313e00-4da1-4b19-a25e-53f121c24d10?api-version=2024-12-01-preview"
                },
            )
        if kwargs.get("url").endswith("contentunderstanding/analyzers/image_analyzer:analyze"):
            return MockResponse(
                status=200,
                headers={
                    "Operation-Location": "https://testcontentunderstanding.cognitiveservices.azure.com/contentunderstanding/analyzers/image_analyzer/results/53e4c016-d2c0-48a9-a9f4-38891f7d45f0?api-version=2024-12-01-preview"
                },
            )
        else:
            raise Exception("Unexpected URL for mock call to ClientSession.post()")

    monkeypatch.setattr(aiohttp.ClientSession, "post", mock_post)

    num_poll_calls = 0

    def mock_get(self, url, **kwargs):
        if url.endswith(
            "contentunderstanding/analyzers/image_analyzer/results/53e4c016-d2c0-48a9-a9f4-38891f7d45f0?api-version=2024-12-01-preview"
        ):
            return MockResponse(
                status=200,
                text=json.dumps(
                    {
                        "id": "f8c4c1c0-71c3-410c-a723-d223e0a84a88",
                        "status": "Succeeded",
                        "result": {
                            "analyzerId": "image_analyzer",
                            "apiVersion": "2024-12-01-preview",
                            "createdAt": "2024-12-05T17:33:04Z",
                            "warnings": [],
                            "contents": [
                                {
                                    "markdown": "![image](image)\n",
                                    "fields": {
                                        "Description": {
                                            "type": "string",
                                            "valueString": "The bar chart titled 'Prices (2024 Indexed to 100)' compares the indexed prices  of Oil, Bitcoin, and S&P 500 from 2024 to 2028. Each year is represented by a set of three horizontal bars, with Oil in gray,  Bitcoin in orange, and S&P 500 in blue. The index is based on the year 2024, where all values start at 100. Over the years, Bitcoin  shows the most significant increase, reaching around 130 by 2028, while Oil and S&P 500 show moderate  increases.\n\n<table><thead><tr><td>Year</td><td>Oil</td><td>Bitcoin</td><td>S&P  500</td></tr></thead><tbody><tr><td>2024</td><td>100</td><td>100</td><td>100</td></tr><tr><td>2025</td><td>105</td><td>110</td><td>1 08</td></tr><tr><td>2026</td><td>110</td><td>115</td><td>112</td></tr><tr><td>2027</td><td>115</td><td>120</td><td>116</td></tr><tr> <td>2028</td><td>120</td><td>130</td><td>120</td></tr></tbody></table>",
                                        }
                                    },
                                    "kind": "document",
                                    "startPageNumber": 1,
                                    "endPageNumber": 1,
                                    "unit": "pixel",
                                    "pages": [{"pageNumber": 1}],
                                }
                            ],
                        },
                    }
                ),
            )
        elif url.endswith(
            "https://testcontentunderstanding.cognitiveservices.azure.com/contentunderstanding/analyzers/badanalyzer/operations/7f313e00-4da1-4b19-a25e-53f121c24d10?api-version=2024-12-01-preview"
        ):
            return MockResponse(status=200, text=json.dumps({"status": "Failed"}))
        elif url.endswith(
            "https://testcontentunderstanding.cognitiveservices.azure.com/contentunderstanding/analyzers/image_analyzer/operations/7f313e00-4da1-4b19-a25e-53f121c24d10?api-version=2024-12-01-preview"
        ):
            nonlocal num_poll_calls
            num_poll_calls += 1
            if num_poll_calls == 1:
                return MockResponse(status=200, text=json.dumps({"status": "Running"}))
            elif num_poll_calls > 1:
                return MockResponse(status=200, text=json.dumps({"status": "Succeeded"}))
        else:
            raise Exception("Unexpected URL for mock call to ClientSession.get()")

    monkeypatch.setattr(aiohttp.ClientSession, "get", mock_get)

    def mock_put(self, *args, **kwargs):
        if kwargs.get("url").find("existinganalyzer") > 0:
            return MockResponse(status=409)
        if kwargs.get("url").find("wrongservicename") > 0:
            return MockResponse(
                status=404,
                text=json.dumps(
                    {"error": {"code": "ResourceNotFound", "message": "The specified resource does not exist."}}
                ),
            )
        elif kwargs.get("url").endswith("contentunderstanding/analyzers/image_analyzer"):
            return MockResponse(
                status=201,
                headers={
                    "Operation-Location": "https://testcontentunderstanding.cognitiveservices.azure.com/contentunderstanding/analyzers/image_analyzer/operations/7f313e00-4da1-4b19-a25e-53f121c24d10?api-version=2024-12-01-preview"
                },
            )
        else:
            raise Exception("Unexpected URL for mock call to ClientSession.put()")

    monkeypatch.setattr(aiohttp.ClientSession, "put", mock_put)

    describer = ContentUnderstandingDescriber(
        endpoint="https://testcontentunderstanding.cognitiveservices.azure.com", credential=MockAzureCredential()
    )
    await describer.create_analyzer()
    await describer.describe_image(b"imagebytes")

    describer_wrong_endpoint = ContentUnderstandingDescriber(
        endpoint="https://wrongservicename.cognitiveservices.azure.com", credential=MockAzureCredential()
    )
    with pytest.raises(Exception):
        await describer_wrong_endpoint.create_analyzer()

    describer_existing_analyzer = ContentUnderstandingDescriber(
        endpoint="https://existinganalyzer.cognitiveservices.azure.com", credential=MockAzureCredential()
    )
    with caplog.at_level(logging.INFO):
        await describer_existing_analyzer.create_analyzer()
        assert "Analyzer 'image_analyzer' already exists." in caplog.text

    describer_bad_analyze = ContentUnderstandingDescriber(
        endpoint="https://badanalyzer.cognitiveservices.azure.com", credential=MockAzureCredential()
    )
    with pytest.raises(Exception):
        await describer_bad_analyze.describe_image(b"imagebytes")


class MockAsyncOpenAI:
    def __init__(self, test_response):
        self.chat = type("MockChat", (), {})()
        self.chat.completions = MockChatCompletions(test_response)


class MockChatCompletions:
    def __init__(self, test_response):
        self.test_response = test_response
        self.create_calls = []

    async def create(self, *args, **kwargs):
        self.create_calls.append(kwargs)
        return self.test_response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model, deployment, expected_model_param",
    [
        ("gpt-4o-mini", None, "gpt-4o-mini"),  # Test with model name only
        ("gpt-4-vision-preview", "my-vision-deployment", "my-vision-deployment"),  # Test with deployment name
    ],
)
async def test_multimodal_model_describer(monkeypatch, model, deployment, expected_model_param):
    # Sample image bytes - a minimal valid PNG
    image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xa3\xb8\xfb\x26\x00\x00\x00\x00IEND\xaeB`\x82"

    # Expected description from the model
    expected_description = "This is a chart showing financial data trends over time."

    # Create a mock OpenAI chat completion response
    mock_response = ChatCompletion(
        id="chatcmpl-123",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(content=expected_description, role="assistant"),
                finish_reason="stop",
            )
        ],
        created=1677652288,
        model=expected_model_param,
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=25, prompt_tokens=50, total_tokens=75),
    )

    # Create mock OpenAI client
    mock_openai_client = MockAsyncOpenAI(mock_response)

    # Create the describer with the mock client
    describer = MultimodalModelDescriber(openai_client=mock_openai_client, model=model, deployment=deployment)

    # Call the method under test
    result = await describer.describe_image(image_bytes)

    # Verify the result matches our expected description
    assert result == expected_description

    # Verify the API was called with the correct parameters
    assert len(mock_openai_client.chat.completions.create_calls) == 1
    call_args = mock_openai_client.chat.completions.create_calls[0]

    # Check model parameter - should be either the model or deployment based on our test case
    assert call_args["model"] == expected_model_param

    # Check that max_tokens was set
    assert call_args["max_tokens"] == 500

    # Check system message
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "helpful assistant" in messages[0]["content"]

    # Check user message with image
    assert messages[1]["role"] == "user"
    assert len(messages[1]["content"]) == 2
    assert messages[1]["content"][0]["type"] == "text"
    assert "Describe image" in messages[1]["content"][0]["text"]
    assert messages[1]["content"][1]["type"] == "image_url"
    assert "data:image/png;base64," in messages[1]["content"][1]["image_url"]["url"]


@pytest.mark.asyncio
async def test_multimodal_model_describer_empty_response(monkeypatch):
    # Sample image bytes
    image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xa3\xb8\xfb\x26\x00\x00\x00\x00IEND\xaeB`\x82"

    # Create mock response with empty content
    mock_response = ChatCompletion(
        id="chatcmpl-789",
        choices=[],  # Empty choices array
        created=1677652288,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=0, prompt_tokens=50, total_tokens=50),
    )

    # Create mock OpenAI client
    mock_openai_client = MockAsyncOpenAI(mock_response)

    # Create the describer
    describer = MultimodalModelDescriber(openai_client=mock_openai_client, model="gpt-4o-mini", deployment=None)

    # Call the method under test
    result = await describer.describe_image(image_bytes)

    # Verify that an empty string is returned when no choices in response
    assert result == ""
