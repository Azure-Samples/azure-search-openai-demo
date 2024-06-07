from promptflow.evals.evaluators import (
    CoherenceEvaluator,
    F1ScoreEvaluator,
    FluencyEvaluator,
    GroundednessEvaluator,
    RelevanceEvaluator,
    SimilarityEvaluator,
)

from .base_metric import BaseMetric


class BuiltinRatingMetric(BaseMetric):

    @classmethod
    def get_aggregate_stats(cls, df):
        return cls.get_aggregate_stats_for_numeric_rating(df, cls.METRIC_NAME)


class BuiltinRelevanceMetric(BuiltinRatingMetric):

    METRIC_NAME = "gpt_relevance"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return RelevanceEvaluator(openai_config)


class BuiltinCoherenceMetric(BuiltinRatingMetric):

    METRIC_NAME = "gpt_coherence"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return CoherenceEvaluator(openai_config)


class BuiltinGroundednessMetric(BuiltinRatingMetric):

    METRIC_NAME = "gpt_groundedness"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return GroundednessEvaluator(openai_config)


class BuiltinSimilarityMetric(BuiltinRatingMetric):

    METRIC_NAME = "gpt_similarity"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return SimilarityEvaluator(openai_config)


class BuiltinFluencyMetric(BuiltinRatingMetric):

    METRIC_NAME = "gpt_fluency"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return FluencyEvaluator(openai_config)


class BuiltinF1ScoreMetric(BaseMetric):

    METRIC_NAME = "f1_score"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        return F1ScoreEvaluator()

    @classmethod
    def get_aggregate_stats(cls, df):
        return {
            "mean": round(df[cls.METRIC_NAME].mean(), 2),
            "max": round(df[cls.METRIC_NAME].max(), 2),
            "min": round(df[cls.METRIC_NAME].min(), 2),
        }
