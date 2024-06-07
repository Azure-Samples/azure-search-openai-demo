from .builtin_metrics import (
    BuiltinCoherenceMetric,
    BuiltinF1ScoreMetric,
    BuiltinFluencyMetric,
    BuiltinGroundednessMetric,
    BuiltinRelevanceMetric,
    BuiltinSimilarityMetric,
)
from .code_metrics import AnswerLengthMetric, CitationMatchMetric, HasCitationMetric, LatencyMetric
from .prompt_metrics import CoherenceMetric, DontKnownessMetric, GroundednessMetric, RelevanceMetric

metrics = [
    BuiltinCoherenceMetric,
    BuiltinRelevanceMetric,
    BuiltinGroundednessMetric,
    BuiltinSimilarityMetric,
    BuiltinFluencyMetric,
    BuiltinF1ScoreMetric,
    CoherenceMetric,
    RelevanceMetric,
    GroundednessMetric,
    DontKnownessMetric,
    LatencyMetric,
    AnswerLengthMetric,
    HasCitationMetric,
    CitationMatchMetric,
]

metrics_by_name = {metric.METRIC_NAME: metric for metric in metrics}
