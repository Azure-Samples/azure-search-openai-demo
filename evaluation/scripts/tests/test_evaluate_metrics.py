import pandas as pd

from scripts.evaluate_metrics import builtin_metrics, code_metrics, prompt_metrics


def test_answer_length():
    metric = code_metrics.AnswerLengthMetric()
    metric_function = metric.evaluator_fn()
    assert callable(metric_function)
    assert metric_function(answer="Hello, world!") == {"answer_length": 13}
    df = pd.DataFrame([{"answer_length": 20}, {"answer_length": 10}, {"answer_length": 5}])
    assert metric.get_aggregate_stats(df) == {"mean": 11.67, "max": 20, "min": 5}


def test_answer_length_new():
    metric = code_metrics.AnswerLengthMetric()
    metric_function = metric.evaluator_fn()
    assert metric_function(answer=None) == {"answer_length": -1}
    df = pd.DataFrame([{"answer_length": 20}, {"answer_length": 10}, {"answer_length": 5}, {"answer_length": -1}])
    assert metric.get_aggregate_stats(df) == {"mean": 11.67, "max": 20, "min": 5}


def test_has_citation():
    metric = code_metrics.HasCitationMetric()
    metric_function = metric.evaluator_fn()
    assert callable(metric_function)
    assert metric_function(answer="Hello, world!") == {"has_citation": False}
    assert metric_function(answer="Hello, [world.pdf]!") == {"has_citation": True}

    df = pd.DataFrame([{"has_citation": True}, {"has_citation": False}, {"has_citation": True}])
    assert metric.get_aggregate_stats(df) == {"total": 2, "rate": 0.67}


def test_has_citation_none():
    metric = code_metrics.HasCitationMetric()
    metric_function = metric.evaluator_fn()
    assert metric_function(answer=None) == {"has_citation": -1}
    df = pd.DataFrame([{"has_citation": True}, {"has_citation": False}, {"has_citation": -1}])
    assert metric.get_aggregate_stats(df) == {"total": 1, "rate": 0.5}


def test_citation_match():
    metric = code_metrics.CitationMatchMetric()
    metric_function = metric.evaluator_fn()
    assert callable(metric_function)
    assert metric_function(ground_truth="answer in [file.pdf]", answer="answer in [file2.pdf]") == {
        "citation_match": False
    }
    assert metric_function(ground_truth="answer in [file2.pdf]", answer="answer in [file2.pdf]") == {
        "citation_match": True
    }
    assert metric_function(ground_truth="answer in [file2.pdf]", answer="answer in [file1.pdf][file2.pdf]") == {
        "citation_match": True
    }
    df = pd.DataFrame([{"citation_match": True}, {"citation_match": False}, {"citation_match": True}])
    assert metric.get_aggregate_stats(df) == {"total": 2, "rate": 0.67}


def test_citation_match_filenames_only():
    truth = 'Use settings like "python.linting.enabled": true, "[python]" [best-practices-for-prompting-github.html]'
    answer = 'Use extension with setting "python.linting.enabled" [best-practices-for-prompting-github.html]'
    metric = code_metrics.CitationMatchMetric()
    metric_function = metric.evaluator_fn()
    assert metric_function(ground_truth=truth, answer=answer) == {"citation_match": True}


def test_citation_match_none():
    metric = code_metrics.CitationMatchMetric()
    metric_function = metric.evaluator_fn()
    assert metric_function(ground_truth="Answer", answer=None) == {"citation_match": -1}
    df = pd.DataFrame([{"citation_match": True}, {"citation_match": False}, {"citation_match": -1}])
    assert metric.get_aggregate_stats(df) == {"total": 1, "rate": 0.5}


def test_latency():
    metric = code_metrics.LatencyMetric()
    metric_function = metric.evaluator_fn()
    assert callable(metric_function)
    assert metric_function(data={"latency": 20}) == {}
    df = pd.DataFrame([{"latency": 20}, {"latency": 10}, {"latency": 5}])
    assert metric.get_aggregate_stats(df) == {"mean": 11.67, "max": 20, "min": 5}


def test_custom_relevance():
    metric = prompt_metrics.RelevanceMetric()

    assert callable(metric.evaluator_fn(openai_config=None))
    df = pd.DataFrame([{"myrelevance": 5}, {"myrelevance": 4}, {"myrelevance": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_custom_coherence():
    metric = prompt_metrics.CoherenceMetric()

    assert callable(metric.evaluator_fn(openai_config=None))
    df = pd.DataFrame([{"mycoherence": 5}, {"mycoherence": 4}, {"mycoherence": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_custom_groundedness():
    metric = prompt_metrics.GroundednessMetric()

    assert callable(metric.evaluator_fn(openai_config=None))
    df = pd.DataFrame([{"mygroundedness": 5}, {"mygroundedness": 4}, {"mygroundedness": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_custom_relevance_missing_values():
    metric = prompt_metrics.RelevanceMetric()

    assert callable(metric.evaluator_fn(openai_config=None))
    df = pd.DataFrame([{"myrelevance": 2}, {"myrelevance": 4}, {"myrelevance": "Failed"}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 3.0, "pass_count": 1, "pass_rate": 0.33}


def test_builtin_coherence():
    metric = builtin_metrics.BuiltinCoherenceMetric()
    assert metric.METRIC_NAME == "gpt_coherence"
    df = pd.DataFrame([{"gpt_coherence": 5}, {"gpt_coherence": 4}, {"gpt_coherence": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_relevance():
    metric = builtin_metrics.BuiltinRelevanceMetric()
    assert metric.METRIC_NAME == "gpt_relevance"
    df = pd.DataFrame([{"gpt_relevance": 5}, {"gpt_relevance": 4}, {"gpt_relevance": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_groundedness():
    metric = builtin_metrics.BuiltinGroundednessMetric()
    assert metric.METRIC_NAME == "gpt_groundedness"
    df = pd.DataFrame([{"gpt_groundedness": 5}, {"gpt_groundedness": 4}, {"gpt_groundedness": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_fluency():
    metric = builtin_metrics.BuiltinFluencyMetric()
    assert metric.METRIC_NAME == "gpt_fluency"
    df = pd.DataFrame([{"gpt_fluency": 5}, {"gpt_fluency": 4}, {"gpt_fluency": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_similarity():
    metric = builtin_metrics.BuiltinSimilarityMetric()
    assert metric.METRIC_NAME == "gpt_similarity"
    df = pd.DataFrame([{"gpt_similarity": 5}, {"gpt_similarity": 4}, {"gpt_similarity": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 4.0, "pass_count": 2, "pass_rate": 0.67}


def test_builtin_f1_score():
    metric = builtin_metrics.BuiltinF1ScoreMetric()
    assert metric.METRIC_NAME == "f1_score"
    df = pd.DataFrame([{"f1_score": 5}, {"f1_score": 4}, {"f1_score": 3}])
    assert metric.get_aggregate_stats(df) == {"mean": 4.0, "max": 5, "min": 3}


def test_builtin_coherence_missing_values():
    metric = builtin_metrics.BuiltinCoherenceMetric()
    assert metric.METRIC_NAME == "gpt_coherence"
    df = pd.DataFrame([{"gpt_coherence": "Failed"}, {"gpt_coherence": 4}, {"gpt_coherence": 3}])
    assert metric.get_aggregate_stats(df) == {"mean_rating": 3.5, "pass_count": 1, "pass_rate": 0.33}
