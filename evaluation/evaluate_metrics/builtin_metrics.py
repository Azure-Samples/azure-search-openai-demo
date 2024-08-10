from promptflow.evals.evaluators import (
    CoherenceEvaluator,
    F1ScoreEvaluator,
    FluencyEvaluator,
    GroundednessEvaluator,
    RelevanceEvaluator,
    SimilarityEvaluator,
)

from .base_metric import DEFAULT_PASSING_THRESHOLD, BaseMetric


class BuiltinRatingMetric(BaseMetric):
    @classmethod
    def get_aggregate_stats(cls, df, passing_threshold=DEFAULT_PASSING_THRESHOLD):
        return cls.get_aggregate_stats_for_numeric_rating(df, cls.METRIC_NAME, passing_threshold)


class BuiltinRelevanceMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_relevance"

    DISPLAY_NAME = "GPT Relevance Rating"
    SHORT_NAME = "Relevance"
    NOTE = "Rating Score (1-5)"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return RelevanceEvaluator(openai_config)


class BuiltinCoherenceMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_coherence"

    DISPLAY_NAME = "GPT Coherence Rating"
    SHORT_NAME = "Coherence"
    NOTE = "Rating Score (1-5)"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return CoherenceEvaluator(openai_config)


class BuiltinGroundednessMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_groundedness"

    DISPLAY_NAME = "GPT Groundedness Rating"
    SHORT_NAME = "Groundedness"
    NOTE = "Rating Score (1-5)"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return GroundednessEvaluator(openai_config)


class BuiltinSimilarityMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_similarity"

    DISPLAY_NAME = "GPT Similarity Rating"
    SHORT_NAME = "Similarity"
    NOTE = "Rating Score (1-5)"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return SimilarityEvaluator(openai_config)


class BuiltinFluencyMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_fluency"

    DISPLAY_NAME = "GPT Fluency Rating"
    SHORT_NAME = "Fluency"
    NOTE = "Rating Score (1-5)"

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return FluencyEvaluator(openai_config)


class BuiltinF1ScoreMetric(BaseMetric):
    METRIC_NAME = "f1_score"

    DISPLAY_NAME = "F1 Score"
    SHORT_NAME = "F1 Score"
    NOTE = "F1 Score"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        return F1ScoreEvaluator()

    @classmethod
    def get_aggregate_stats(cls, df, passing_threshold=DEFAULT_PASSING_THRESHOLD):
        return {
            "mean": round(df[cls.METRIC_NAME].mean(), 2),
            "max": round(df[cls.METRIC_NAME].max(), 2),
            "min": round(df[cls.METRIC_NAME].min(), 2),
        }
