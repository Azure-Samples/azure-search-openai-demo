import pandas as pd

from evaltools.eval.evaluate_metrics import builtin_metrics, code_metrics


def test_answer_length():
    metric = code_metrics.AnswerLengthMetric()
    fn = metric.evaluator_fn()
    assert callable(fn)
    assert fn(response="Hello, world!") == {"answer_length": 13}
    assert fn(response="") == {"answer_length": 0}
    df = pd.DataFrame([{"answer_length": 10}, {"answer_length": 20}, {"answer_length": 30}])
    assert metric.get_aggregate_stats(df) == {"mean": 20.0, "max": 30, "min": 10}


def test_answer_length_none():
    metric = code_metrics.AnswerLengthMetric()
    fn = metric.evaluator_fn()
    assert fn(response=None) == {"answer_length": -1}
    # -1 values are excluded from the aggregate
    df = pd.DataFrame([{"answer_length": 10}, {"answer_length": 20}, {"answer_length": -1}])
    assert metric.get_aggregate_stats(df) == {"mean": 15.0, "max": 20, "min": 10}


def test_any_citation():
    metric = code_metrics.AnyCitationMetric()
    fn = metric.evaluator_fn()
    assert callable(fn)
    assert fn(response="Hello, world!") == {"any_citation": False}
    assert fn(response="Hello, [world.pdf]!") == {"any_citation": True}
    df = pd.DataFrame([{"any_citation": True}, {"any_citation": False}, {"any_citation": True}])
    assert metric.get_aggregate_stats(df) == {"total": 2, "rate": 0.67}


def test_any_citation_none():
    metric = code_metrics.AnyCitationMetric()
    fn = metric.evaluator_fn()
    assert fn(response=None) == {"any_citation": -1}
    # -1 values are excluded from the aggregate
    df = pd.DataFrame([{"any_citation": True}, {"any_citation": False}, {"any_citation": -1}])
    assert metric.get_aggregate_stats(df) == {"total": 1, "rate": 0.5}


def test_citations_matched():
    metric = code_metrics.CitationsMatchedMetric()
    fn = metric.evaluator_fn()
    assert callable(fn)
    # No overlap -> 0.0
    assert fn(ground_truth="answer in [file1.pdf]", response="answer in [file2.pdf]") == {"citations_matched": 0.0}
    # Exact match -> 1.0
    assert fn(ground_truth="answer in [file2.pdf]", response="answer in [file2.pdf]") == {"citations_matched": 1.0}
    # Response has extra citations but includes the truth one -> 1.0
    assert fn(ground_truth="answer in [file2.pdf]", response="[file1.pdf][file2.pdf]") == {"citations_matched": 1.0}
    # Partial: 1 of 2 truth citations matched -> 0.5
    assert fn(ground_truth="[file1.pdf][file2.pdf]", response="[file2.pdf]") == {"citations_matched": 0.5}
    df = pd.DataFrame([{"citations_matched": 1.0}, {"citations_matched": 0.0}, {"citations_matched": 0.5}])
    assert metric.get_aggregate_stats(df) == {"total": 1, "rate": 0.5}


def test_citations_matched_with_page_anchors():
    metric = code_metrics.CitationsMatchedMetric()
    fn = metric.evaluator_fn()
    truth = "The answer [Northwind_Standard_Benefits_Details.pdf#page=7]"
    response = "The answer [Northwind_Standard_Benefits_Details.pdf#page=7]"
    assert fn(ground_truth=truth, response=response) == {"citations_matched": 1.0}


def test_citations_matched_none():
    metric = code_metrics.CitationsMatchedMetric()
    fn = metric.evaluator_fn()
    assert fn(ground_truth="Answer [file.pdf]", response=None) == {"citations_matched": -1}
    # -1 values are excluded from the aggregate
    df = pd.DataFrame([{"citations_matched": 1.0}, {"citations_matched": 0.0}, {"citations_matched": -1}])
    assert metric.get_aggregate_stats(df) == {"total": 1, "rate": 0.5}


def test_latency():
    metric = code_metrics.LatencyMetric()
    fn = metric.evaluator_fn()
    assert callable(fn)
    # latency() returns no extra data, since it is already stored in the response
    assert fn(data={"latency": 20}) == {}
    df = pd.DataFrame([{"latency": 20}, {"latency": 10}, {"latency": 5}, {"latency": -1}])
    assert metric.get_aggregate_stats(df) == {"mean": 11.67, "max": 20, "min": 5}


def test_latency_all_requests_failed():
    metric = code_metrics.LatencyMetric()
    df = pd.DataFrame([{"latency": -1}, {"latency": -1}])
    assert metric.get_aggregate_stats(df) == {"mean": 0, "max": 0, "min": 0}


def test_builtin_relevance():
    metric = builtin_metrics.BuiltinRelevanceMetric()
    assert metric.METRIC_NAME == "gpt_relevance"
    assert metric.RATING_COLUMN == "relevance"
    df = pd.DataFrame([{"relevance": 5}, {"relevance": 4}, {"relevance": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_coherence():
    metric = builtin_metrics.BuiltinCoherenceMetric()
    assert metric.METRIC_NAME == "gpt_coherence"
    assert metric.RATING_COLUMN == "coherence"
    df = pd.DataFrame([{"coherence": 5}, {"coherence": 4}, {"coherence": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_groundedness():
    metric = builtin_metrics.BuiltinGroundednessMetric()
    assert metric.METRIC_NAME == "gpt_groundedness"
    assert metric.RATING_COLUMN == "groundedness"
    df = pd.DataFrame([{"groundedness": 5}, {"groundedness": 4}, {"groundedness": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_similarity():
    metric = builtin_metrics.BuiltinSimilarityMetric()
    assert metric.METRIC_NAME == "gpt_similarity"
    assert metric.RATING_COLUMN == "similarity"
    df = pd.DataFrame([{"similarity": 5}, {"similarity": 4}, {"similarity": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_fluency():
    metric = builtin_metrics.BuiltinFluencyMetric()
    assert metric.METRIC_NAME == "gpt_fluency"
    assert metric.RATING_COLUMN == "fluency"
    df = pd.DataFrame([{"fluency": 5}, {"fluency": 4}, {"fluency": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_metrics_use_supplied_credential(monkeypatch):
    credential = object()
    openai_config = {
        "azure_endpoint": "https://example.openai.azure.com",
        "azure_deployment": "eval",
    }
    metric_evaluators = [
        (builtin_metrics.BuiltinRelevanceMetric, "RelevanceEvaluator"),
        (builtin_metrics.BuiltinCoherenceMetric, "CoherenceEvaluator"),
        (builtin_metrics.BuiltinGroundednessMetric, "GroundednessEvaluator"),
        (builtin_metrics.BuiltinSimilarityMetric, "SimilarityEvaluator"),
        (builtin_metrics.BuiltinFluencyMetric, "FluencyEvaluator"),
    ]

    for metric, evaluator_name in metric_evaluators:
        captured = {}

        def evaluator(model_config, **kwargs):
            captured["model_config"] = model_config
            captured["credential"] = kwargs["credential"]
            captured["is_reasoning_model"] = kwargs["is_reasoning_model"]
            return object()

        monkeypatch.setattr(builtin_metrics, evaluator_name, evaluator)
        metric.evaluator_fn(openai_config=openai_config, azure_credential=credential)

        assert captured == {
            "model_config": openai_config,
            "credential": credential,
            "is_reasoning_model": True,
        }


def test_builtin_rating_missing_values():
    metric = builtin_metrics.BuiltinCoherenceMetric()
    # Non-numeric ratings (e.g. "Failed") are coerced to NaN and dropped
    df = pd.DataFrame([{"coherence": "Failed"}, {"coherence": 4}, {"coherence": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 3.5, "pass_count": 1, "pass_rate": 0.33}


def test_builtin_f1_score():
    metric = builtin_metrics.BuiltinF1ScoreMetric()
    assert metric.METRIC_NAME == "f1_score"
    df = pd.DataFrame([{"f1_score": 5}, {"f1_score": 4}, {"f1_score": 3}])
    assert metric.get_aggregate_stats(df) == {"mean": 4.0, "max": 5, "min": 3}
