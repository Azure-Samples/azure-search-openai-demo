import json
from datetime import timedelta

import pytest
import requests

from evaltools.eval.evaluate import send_question_to_target

SCHEMA_ERROR_TEMPLATE = (
    "Response does not adhere to the expected schema. "
    "The answer should be accessible via the JMESPath expression 'output_text' "
    "and the context should be accessible via the JMESPath expression 'context.data_points.text'. "
    "Either adjust the app response or adjust send_question_to_target() in evaluate.py "
    "to match the actual schema.\nResponse: {response}"
)


class MockResponse:
    def __init__(self, json_data, text="", raise_json_error=False, status_code=200):
        self.json_data = json_data
        self.text = text
        self.encoding = "utf-8"
        self.raise_json_error = raise_json_error
        self.elapsed = timedelta(seconds=1)
        self.status_code = status_code

    def json(self):
        if self.raise_json_error:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error", response=self)


def test_send_question_to_target_valid(monkeypatch):
    response = {
        "output_text": "This is the answer",
        "context": {"data_points": {"text": ["Context 1", "Context 2"]}},
    }
    monkeypatch.setattr(requests, "post", lambda url, headers, json, **kwargs: MockResponse(response))
    result = send_question_to_target("Question 1", "http://example.com")
    assert result["answer"] == "This is the answer"
    assert result["context"] == "Context 1\n\nContext 2"
    assert result["latency"] == 1


def test_send_question_to_target_missing_error_stored(monkeypatch):
    response = {}
    monkeypatch.setattr(requests, "post", lambda url, headers, json, **kwargs: MockResponse(response))
    result = send_question_to_target("Question", "http://example.com")
    expected = SCHEMA_ERROR_TEMPLATE.format(response={})
    assert result["answer"] == expected
    assert result["context"] == expected
    assert result["latency"] == -1


def test_send_question_to_target_missing_all_raises(monkeypatch):
    response = {}
    monkeypatch.setattr(requests, "post", lambda url, headers, json, **kwargs: MockResponse(response))
    with pytest.raises(ValueError) as exc_info:
        send_question_to_target("Question", "http://example.com", raise_error=True)
    assert str(exc_info.value) == SCHEMA_ERROR_TEMPLATE.format(response={})


def test_send_question_to_target_missing_context_raises(monkeypatch):
    response = {"output_text": "This is the answer"}
    monkeypatch.setattr(requests, "post", lambda url, headers, json, **kwargs: MockResponse(response))
    with pytest.raises(ValueError) as exc_info:
        send_question_to_target("Question", "http://example.com", raise_error=True)
    assert str(exc_info.value) == SCHEMA_ERROR_TEMPLATE.format(response=response)


def test_send_question_to_target_invalid_json_raises(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, headers, json, **kwargs: MockResponse(None, text="not json", raise_json_error=True),
    )
    with pytest.raises(ValueError) as exc_info:
        send_question_to_target("Question", "http://example.com", raise_error=True)
    assert "is not valid JSON" in str(exc_info.value)
    assert "not json" in str(exc_info.value)


def test_send_question_to_target_dict_context(monkeypatch):
    response = {
        "output_text": "The answer",
        "context": {"data_points": {"text": {"doc1": "Context A"}}},
    }
    monkeypatch.setattr(requests, "post", lambda url, headers, json, **kwargs: MockResponse(response))
    result = send_question_to_target("Question", "http://example.com")
    assert result["answer"] == "The answer"
    assert result["context"] == json.dumps({"doc1": "Context A"}, ensure_ascii=False)


def test_send_question_to_target_http_error_raises(monkeypatch):
    # A 4xx/5xx response should surface as an HTTPError (via raise_for_status) rather
    # than being misreported as a JSON/schema problem.
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, headers, json, **kwargs: MockResponse(None, text="Internal Server Error", status_code=500),
    )
    with pytest.raises(requests.HTTPError) as exc_info:
        send_question_to_target("Question", "http://example.com", raise_error=True)
    assert "500" in str(exc_info.value)


def test_send_question_to_target_http_error_stored(monkeypatch):
    # When raise_error is False, the HTTP error is stored in the answer/context fields.
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, headers, json, **kwargs: MockResponse(None, text="Not Found", status_code=404),
    )
    result = send_question_to_target("Question", "http://example.com")
    assert "404" in result["answer"]
    assert result["latency"] == -1
