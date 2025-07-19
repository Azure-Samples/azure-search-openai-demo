import json
import logging

import aiohttp
import pytest

from prepdocslib.mediadescriber import ContentUnderstandingDescriber

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
