import logging
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger("scripts")


class BaseMetric(ABC):

    METRIC_NAME = "name_of_metric"

    @classmethod
    @abstractmethod
    def get_aggregate_stats(cls, df):
        """Returns a dictionary of aggregate statistics for the metric"""
        pass

    @classmethod
    def get_aggregate_stats_for_numeric_rating(cls, df, rating_column_name):
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

        # Count how many ratings passed threshold of 4+
        pass_count = int(df[rating_column_name].apply(lambda rating: rating >= 4).sum())

        return {
            "pass_count": pass_count,
            "pass_rate": round(pass_count / rows_before, 2),
            "mean_rating": round(df[rating_column_name].mean(), 2),
        }
