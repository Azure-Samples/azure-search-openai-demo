import logging
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger("evaluation")

DEFAULT_PASSING_THRESHOLD = 4.0


class BaseMetric(ABC):
    METRIC_NAME = "name_of_metric"

    @classmethod
    @abstractmethod
    def get_aggregate_stats(cls, df, passing_threshold=DEFAULT_PASSING_THRESHOLD):
        """Returns a dictionary of aggregate statistics for the metric"""
        pass

    @classmethod
    def get_aggregate_stats_for_numeric_rating(cls, df, rating_column_name, passing_threshold):
        # Narrow down dataframe to just the metric

        df = df[[rating_column_name]]

        # Drop invalid ratings - strings like "Failed"
        rows_before = len(df)
        df = df.apply(pd.to_numeric, errors="coerce")
        df = df.dropna()
        rows_after = len(df)
        if rows_before != rows_after:
            logger.warning(
                "Dropped %d invalid ratings for metric %s",
                rows_before - rows_after,
                rating_column_name,
            )

        # Count how many ratings passed threshold of passing rate
        pass_count = int(df[rating_column_name].apply(lambda rating: rating >= passing_threshold).sum())

        return {
            "pass_count": pass_count,
            "pass_rate": round(pass_count / rows_before, 2),
            "mean_rating": round(df[rating_column_name].mean(), 2),
        }
