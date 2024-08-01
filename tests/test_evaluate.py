import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

import requests
from promptflow.core import AzureOpenAIModelConfiguration

from evaluation.evaluate import evaluate_row, run_evaluation, send_question_to_target
from evaluation.evaluate_metrics import metrics_by_name


def test_evaluate_row():
    row = {"question": "What is the capital of France?", "truth": "Paris"}

    response = {
        "message": {"content": "This is the answer"},
        "context": {"data_points": {"text": ["Context 1", "Context 2"]}},
    }

    requests.post = lambda url, headers, json: MockResponse(response, url=url)
    target_url = "http://mock-target-url.com"
    openai_config = AzureOpenAIModelConfiguration("azure")
    openai_config.model = "mock_model"
    result = evaluate_row(
        row=row,
        target_url=target_url,
        openai_config=openai_config,
        requested_metrics=[MockMetric],
        target_parameters={},
    )

    assert result["question"] == "What is the capital of France?"
    assert result["truth"] == "Paris"
    assert "answer" in result
    assert "context" in result
    assert "latency" in result
    assert result["mock_metric_score"] == 1.0


def test_send_question_to_target_valid():
    # Test case 1: Valid response
    response = {
        "message": {"content": "This is the answer"},
        "context": {"data_points": {"text": ["Context 1", "Context 2"]}},
    }
    requests.post = lambda url, headers, json: MockResponse(response, url=url)
    result = send_question_to_target("Question 1", "http://example.com")
    assert result["answer"] == "This is the answer"
    assert result["context"] == "Context 1\n\nContext 2"
    assert result["latency"] == 1


def test_send_question_to_target_missing_error_store():
    response = {}
    requests.post = lambda url, headers, json: MockResponse(response, url=url)
    result = send_question_to_target("Question", "http://example.com", raise_error=False)
    assert result["answer"] == (
        "Response does not adhere to the expected schema. \n"
        "Either adjust the app response or adjust send_question_to_target() to match the actual schema.\n"
        "Response: {}"
    )
    assert result["context"] == (
        "Response does not adhere to the expected schema. \n"
        "Either adjust the app response or adjust send_question_to_target() to match the actual schema.\n"
        "Response: {}"
    )


def test_send_question_to_target_missing_all():
    response = {}
    requests.post = lambda url, headers, json: MockResponse(response, url=url)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert str(e) == (
            "Response does not adhere to the expected schema. \n"
            "Either adjust the app response or adjust send_question_to_target() to match the actual schema.\n"
            "Response: {}"
        )


def test_send_question_to_target_missing_content():
    response = {
        "message": {},
        "context": {"data_points": {"text": ["Context 1", "Context 2"]}},
    }
    requests.post = lambda url, headers, json: MockResponse(response, url=url)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert str(e) == (
            "Response does not adhere to the expected schema. \n"
            "Either adjust the app response or adjust send_question_to_target() to match the actual schema.\n"
            "Response: {'message': {}, 'context': {'data_points': {'text': ['Context 1', 'Context 2']}}}"
        )


def test_send_question_to_target_missing_context():
    # Test case 5: Missing 'context' key in response
    response = {"message": {"content": "This is the answer"}}
    requests.post = lambda url, headers, json: MockResponse(response, url=url)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert str(e) == (
            "Response does not adhere to the expected schema. \n"
            "Either adjust the app response or adjust send_question_to_target() to match the actual schema.\n"
            "Response: {'message': {'content': 'This is the answer'}}"
        )


def test_send_question_to_target_request_failed():
    # Test case 6: Request failed, response status code is 500
    requests.post = lambda url, headers, json: MockResponse(None, status_code=500, url=url)
    try:
        send_question_to_target("Question", "Answer", "http://example.com", raise_error=True)
    except Exception as e:
        assert isinstance(e, requests.HTTPError)


def test_run_evaluation():
    with tempfile.TemporaryDirectory() as tempdir:
        testdata_path = Path(tempdir) / "test_data.jsonl"
        results_dir = Path(tempdir) / "results"

        with mock.patch("evaluation.evaluate.load_jsonl", return_value=[{"question": "What is 2 + 2?", "truth": "4"}]):
            with mock.patch("evaluation.evaluate.summarize_results_and_plot"):
                with mock.patch("evaluation.evaluate.service_setup.get_openai_config", return_value={}):
                    with mock.patch(
                        "evaluation.evaluate.send_question_to_target",
                        return_value={"answer": "4", "context": "2 + 2 = 4", "latency": 1.0},
                    ):

                        metrics_by_name["mock_metric"] = type(
                            "MockMetric",
                            (),
                            {
                                "METRIC_NAME": "mock_metric",
                                "evaluator_fn": staticmethod(
                                    lambda openai_config: lambda question, answer, context, ground_truth: {
                                        "mock_metric_score": 3.0
                                    }
                                ),
                                "get_aggregate_stats": staticmethod(
                                    lambda df, passing_rate: {"pass_rate": 0.67, "mean_rating": 3.0}
                                ),
                            },
                        )

                        openai_config = AzureOpenAIModelConfiguration("azure")
                        openai_config.model = "mock_model"
                        target_url = "http://mock-target-url.com"
                        passing_rate = 3
                        max_workers = 2
                        target_parameters = {}
                        requested_metrics = ["mock_metric"]

                        success = run_evaluation(
                            openai_config=openai_config,
                            testdata_path=testdata_path,
                            results_dir=results_dir,
                            target_url=target_url,
                            passing_rate=passing_rate,
                            max_workers=max_workers,
                            target_parameters=target_parameters,
                            requested_metrics=requested_metrics,
                        )

                        assert success


class MockResponse:
    def __init__(self, json_data, status_code=200, reason="Fail Test", url="http://mock-url.com"):
        self.json_data = json_data
        self.status_code = status_code
        self.reason = reason
        self.elapsed = timedelta(seconds=1)
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.reason)

    @property
    def ok(self):
        return self.status_code >= 200 and self.status_code < 400

    def json(self):
        return self.json_data


class MockMetric:
    METRIC_NAME = "mock_metric"

    @staticmethod
    def evaluator_fn(openai_config):
        return lambda question, answer, context, ground_truth: {"mock_metric_score": 1.0}
