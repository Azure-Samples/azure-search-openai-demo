from .builtin_metrics import (
    BuiltinCoherenceMetric,
    BuiltinF1ScoreMetric,
    BuiltinFluencyMetric,
    BuiltinGroundednessMetric,
    BuiltinRelevanceMetric,
    BuiltinSimilarityMetric,
)
from .code_metrics import (
    AnswerLengthMetric,
    AnyCitationMetric,
    CitationsMatchedMetric,
    LatencyMetric,
)

metrics = [
    BuiltinCoherenceMetric,
    BuiltinRelevanceMetric,
    BuiltinGroundednessMetric,
    BuiltinSimilarityMetric,
    BuiltinFluencyMetric,
    BuiltinF1ScoreMetric,
    LatencyMetric,
    AnswerLengthMetric,
    AnyCitationMetric,
    CitationsMatchedMetric,
]

metrics_by_name = {metric.METRIC_NAME: metric for metric in metrics}


def register_metric(metric_class):
    """Register a new custom metric class."""
    if not hasattr(metric_class, "METRIC_NAME"):
        raise ValueError("Metric class must have a METRIC_NAME attribute")
    # Check if the metric name is already registered
    if metric_class.METRIC_NAME in metrics_by_name:
        raise ValueError(f"Metric with name {metric_class.METRIC_NAME} is already registered")
    metrics_by_name[metric_class.METRIC_NAME] = metric_class
