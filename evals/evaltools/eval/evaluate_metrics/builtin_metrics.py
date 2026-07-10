from azure.ai.evaluation import (
    CoherenceEvaluator,
    F1ScoreEvaluator,
    FluencyEvaluator,
    GroundednessEvaluator,
    RelevanceEvaluator,
    SimilarityEvaluator,
)

from .base_metric import BaseMetric

# The LLM-judged evaluators are constructed with is_reasoning_model=True so that
# they send `max_completion_tokens` instead of `max_tokens`. Reasoning models
# such as gpt-5 reject `max_tokens`, and passing this flag is safe for
# non-reasoning models too. Requires azure-ai-evaluation>=1.18.0.


class BuiltinRatingMetric(BaseMetric):
    # The registry key / summary key (METRIC_NAME) stays `gpt_*` for backwards
    # compatibility with evaluate_config.json and existing result baselines, but
    # azure-ai-evaluation>=1.11 emits the raw rating under an unprefixed column
    # name (e.g. `groundedness`), so aggregation reads RATING_COLUMN instead.
    RATING_COLUMN = None

    @classmethod
    def get_aggregate_stats(cls, df):
        return cls.get_aggregate_stats_for_numeric_rating(df, cls.RATING_COLUMN or cls.METRIC_NAME)


class BuiltinRelevanceMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_relevance"
    RATING_COLUMN = "relevance"

    @classmethod
    def evaluator_fn(cls, openai_config, azure_credential=None, **kwargs):
        return RelevanceEvaluator(openai_config, credential=azure_credential, is_reasoning_model=True)


class BuiltinCoherenceMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_coherence"
    RATING_COLUMN = "coherence"

    @classmethod
    def evaluator_fn(cls, openai_config, azure_credential=None, **kwargs):
        return CoherenceEvaluator(openai_config, credential=azure_credential, is_reasoning_model=True)


class BuiltinGroundednessMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_groundedness"
    RATING_COLUMN = "groundedness"

    @classmethod
    def evaluator_fn(cls, openai_config, azure_credential=None, **kwargs):
        return GroundednessEvaluator(openai_config, credential=azure_credential, is_reasoning_model=True)


class BuiltinSimilarityMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_similarity"
    RATING_COLUMN = "similarity"

    @classmethod
    def evaluator_fn(cls, openai_config, azure_credential=None, **kwargs):
        return SimilarityEvaluator(openai_config, credential=azure_credential, is_reasoning_model=True)


class BuiltinFluencyMetric(BuiltinRatingMetric):
    METRIC_NAME = "gpt_fluency"
    RATING_COLUMN = "fluency"

    @classmethod
    def evaluator_fn(cls, openai_config, azure_credential=None, **kwargs):
        return FluencyEvaluator(openai_config, credential=azure_credential, is_reasoning_model=True)


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
