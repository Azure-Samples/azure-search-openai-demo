import logging
import re

from .base_metric import BaseMetric

logger = logging.getLogger("evaltools")

# Regex pattern to match citations of the forms:
# [Document Name.pdf#page=7]
# [Document Name.pdf#page=4(figure4_1.png)]
# and supports multiple document extensions such as:
#  pdf, html/htm, doc/docx, ppt/pptx, xls/xlsx, csv, txt, json,
#  images: jpg/jpeg, png, bmp, tiff/tif, heif/heiff
# Optional components:
#   #page=\d+           -> page anchor (primarily for paged docs like PDFs)
#   ( ... )              -> figure/image or sub-resource reference (e.g., (figure4_1.png))
CITATION_REGEX = re.compile(
    r"\[[^\]]+?\.(?:pdf|html?|docx?|pptx?|xlsx?|csv|txt|json|jpe?g|png|bmp|tiff?|heiff?|heif)(?:#page=\d+)?(?:\([^()\]]+\))?\]",
    re.IGNORECASE,
)


class AnswerLengthMetric(BaseMetric):
    METRIC_NAME = "answer_length"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def answer_length(*, response, **kwargs):
            if response is None:
                logger.warning("Received response of None, can't compute answer_length metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            return {cls.METRIC_NAME: len(response)}

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


class AnyCitationMetric(BaseMetric):
    METRIC_NAME = "any_citation"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def any_citation(*, response, **kwargs):
            if response is None:
                logger.warning("Received response of None, can't compute any_citation metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            return {cls.METRIC_NAME: bool(CITATION_REGEX.search(response))}

        return any_citation

    @classmethod
    def get_aggregate_stats(cls, df):
        df = df[df[cls.METRIC_NAME] != -1]
        return {
            "total": int(df[cls.METRIC_NAME].sum()),
            "rate": round(df[cls.METRIC_NAME].mean(), 2),
        }


class CitationsMatchedMetric(BaseMetric):
    METRIC_NAME = "citations_matched"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def citations_matched(*, response, ground_truth, **kwargs):
            if response is None:
                logger.warning("Received response of None, can't compute citations_matched metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            # Extract full citation tokens from ground truth and response
            truth_citations = set(CITATION_REGEX.findall(ground_truth or ""))
            response_citations = set(CITATION_REGEX.findall(response or ""))
            # Count the percentage of citations that are present in the response
            num_citations = len(truth_citations)
            if num_citations == 0:
                logger.warning("Ground truth has no citations, can't compute citations_matched metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            num_matched_citations = len(truth_citations.intersection(response_citations))
            return {cls.METRIC_NAME: num_matched_citations / num_citations}

        return citations_matched

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
        df = df[df[cls.METRIC_NAME] != -1]
        if df.empty:
            logger.warning("No successful requests available for latency metric")
            return {"mean": 0, "max": 0, "min": 0}
        return {
            "mean": round(df[cls.METRIC_NAME].mean(), 2),
            "max": df[cls.METRIC_NAME].max(),
            "min": df[cls.METRIC_NAME].min(),
        }
