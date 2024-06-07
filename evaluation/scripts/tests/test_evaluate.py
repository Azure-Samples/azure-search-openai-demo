from datetime import timedelta

import requests

from scripts.evaluate import send_question_to_target


def test_send_question_to_target_valid():
    # Test case 1: Valid response
    response = {
        "message": {"content": "This is the answer"},
        "context": {"data_points": {"text": ["Context 1", "Context 2"]}},
    }
    requests.post = lambda url, headers, json: MockResponse(response)
    result = send_question_to_target("Question 1", "http://example.com")
    assert result["answer"] == "This is the answer"
    assert result["context"] == "Context 1\n\nContext 2"
    assert result["latency"] == 1


def test_send_question_to_target_missing_error_store():
    response = {}
    requests.post = lambda url, headers, json: MockResponse(response)
    result = send_question_to_target("Question", "http://example.com")
    assert result["answer"] == (
        "Response does not adhere to the expected schema. "
        "The answer should be accessible via the JMESPath expression 'message.content' "
        "and the context should be accessible via the JMESPath expression 'context.data_points.text'. "
        "Either adjust the app response or adjust send_question_to_target() "
        "in evaluate.py to match the actual schema.\n"
        "Response: {}"
    )
    assert result["context"] == (
        "Response does not adhere to the expected schema. "
        "The answer should be accessible via the JMESPath expression 'message.content' "
        "and the context should be accessible via the JMESPath expression 'context.data_points.text'. "
        "Either adjust the app response or adjust send_question_to_target() "
        "in evaluate.py to match the actual schema.\n"
        "Response: {}"
    )


def test_send_question_to_target_missing_all():
    response = {}
    requests.post = lambda url, headers, json: MockResponse(response)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert str(e) == (
            "Response does not adhere to the expected schema. "
            "The answer should be accessible via the JMESPath expression 'message.content' "
            "and the context should be accessible via the JMESPath expression 'context.data_points.text'. "
            "Either adjust the app response or adjust send_question_to_target() "
            "in evaluate.py to match the actual schema.\n"
            "Response: {}"
        )


def test_send_question_to_target_missing_content():
    response = {"message": {}, "context": {"data_points": {"text": ["Context 1", "Context 2"]}}}
    requests.post = lambda url, headers, json: MockResponse(response)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert str(e) == (
            "Response does not adhere to the expected schema. "
            "The answer should be accessible via the JMESPath expression 'message.content' "
            "and the context should be accessible via the JMESPath expression 'context.data_points.text'. "
            "Either adjust the app response or adjust send_question_to_target() "
            "in evaluate.py to match the actual schema.\n"
            "Response: {'message': {}, 'context': {'data_points': {'text': ['Context 1', 'Context 2']}}}"
        )


def test_send_question_to_target_missing_context():
    # Test case 5: Missing 'context' key in response
    response = {"message": {"content": "This is the answer"}}
    requests.post = lambda url, headers, json: MockResponse(response)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert str(e) == (
            "Response does not adhere to the expected schema. "
            "The answer should be accessible via the JMESPath expression 'message.content' "
            "and the context should be accessible via the JMESPath expression 'context.data_points.text'. "
            "Either adjust the app response or adjust send_question_to_target() "
            "in evaluate.py to match the actual schema.\n"
            "Response: {'message': {'content': 'This is the answer'}}"
        )


class MockResponse:
    def __init__(self, json_data):
        self.json_data = json_data
        self.elapsed = timedelta(seconds=1)

    def json(self):
        return self.json_data
