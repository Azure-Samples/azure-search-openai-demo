import logging
import re

from .base_metric import BaseMetric

logger = logging.getLogger("scripts")


class AnswerLengthMetric(BaseMetric):

    METRIC_NAME = "answer_length"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def answer_length(*, answer, **kwargs):
            if answer is None:
                logger.warning("Received answer of None, can't compute answer_length metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            return {cls.METRIC_NAME: len(answer)}

        return answer_length

    @classmethod
    def get_aggregate_stats(cls, df):
        # remove -1 values from the mean calculation
        df = df[df[cls.METRIC_NAME] != -1]
        return {
            "mean": round(df[cls.METRIC_NAME].mean(), 2),
            "max": int(df[cls.METRIC_NAME].max()),
            "min": int(df[cls.METRIC_NAME].min()),
        }


class HasCitationMetric(BaseMetric):

    METRIC_NAME = "has_citation"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def has_citation(*, answer, **kwargs):
            if answer is None:
                logger.warning("Received answer of None, can't compute has_citation metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            return {cls.METRIC_NAME: bool(re.search(r"\[[^\]]+\]", answer))}

        return has_citation

    @classmethod
    def get_aggregate_stats(cls, df):
        df = df[df[cls.METRIC_NAME] != -1]
        return {
            "total": int(df[cls.METRIC_NAME].sum()),
            "rate": round(df[cls.METRIC_NAME].mean(), 2),
        }


class CitationMatchMetric(BaseMetric):

    METRIC_NAME = "citation_match"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def citation_match(*, answer, ground_truth, **kwargs):
            if answer is None:
                logger.warning("Received answer of None, can't compute citation_match metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            # Return true if all citations in the truth are present in the answer
            truth_citations = set(re.findall(r"\[([^\]]+)\.\w{3,4}\]", ground_truth))
            answer_citations = set(re.findall(r"\[([^\]]+)\.\w{3,4}\]", answer))
            citation_match = truth_citations.issubset(answer_citations)
            return {cls.METRIC_NAME: citation_match}

        return citation_match

    @classmethod
    def get_aggregate_stats(cls, df):
        df = df[df[cls.METRIC_NAME] != -1]
        return {
            "total": int(df[cls.METRIC_NAME].sum()),
            "rate": round(df[cls.METRIC_NAME].mean(), 2),
        }


class LatencyMetric(BaseMetric):

    METRIC_NAME = "latency"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def latency(**kwargs):
            # Return no additional data, since latency is already stored in the target response
            return {}

        return latency

    @classmethod
    def get_aggregate_stats(cls, df):
        return {
            "mean": round(df[cls.METRIC_NAME].mean(), 2),
            "max": df[cls.METRIC_NAME].max(),
            "min": df[cls.METRIC_NAME].min(),
        }
