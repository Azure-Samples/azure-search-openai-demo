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
    CitationMatchMetric,
    HasCitationMetric,
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
    HasCitationMetric,
    CitationMatchMetric,
]

metrics_by_name = {metric.METRIC_NAME: metric for metric in metrics}
