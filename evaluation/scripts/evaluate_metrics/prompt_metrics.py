import logging
import re
from pathlib import Path

import numpy as np
from promptflow.client import load_flow

from .base_metric import BaseMetric

PROMPT_TEMPLATE_DIR = Path(__file__).resolve().parent / "prompts"

logger = logging.getLogger("scripts")


class PromptBasedEvaluator:

    def __init__(self, model_config, path, name):
        prompty_model_config = {"configuration": model_config}
        self._name = name
        self._flow = load_flow(source=path, model=prompty_model_config)

    def __call__(self, **kwargs) -> dict:
        llm_output = self._flow(**kwargs)

        score = np.nan
        if llm_output:
            match = re.search(r"\d", llm_output)
            if match:
                score = float(match.group())
            else:
                logging.warning(
                    "No score found in answer: %s\nMake sure prompty file is correctly formatted.", llm_output
                )

        output = {}
        output[self._name] = float(score)
        return output


class CustomRatingMetric(BaseMetric):

    @classmethod
    def evaluator_fn(cls, openai_config, **kwargs):
        return PromptBasedEvaluator(
            openai_config, path=PROMPT_TEMPLATE_DIR / f"{cls.METRIC_NAME}.prompty", name=cls.METRIC_NAME
        )

    @classmethod
    def get_aggregate_stats(cls, df):
        return cls.get_aggregate_stats_for_numeric_rating(df, cls.METRIC_NAME)


class RelevanceMetric(CustomRatingMetric):

    METRIC_NAME = "myrelevance"


class CoherenceMetric(CustomRatingMetric):

    METRIC_NAME = "mycoherence"


class GroundednessMetric(CustomRatingMetric):

    METRIC_NAME = "mygroundedness"


class DontKnownessMetric(CustomRatingMetric):

    METRIC_NAME = "dontknowness"
