import concurrent.futures
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from promptflow.core import AzureOpenAIModelConfiguration
from rich.progress import track

from evaluation import service_setup
from evaluation.evaluate_metrics import metrics_by_name
from evaluation.evaluate_metrics.builtin_metrics import BuiltinRatingMetric
from evaluation.plotting import (
    plot_bar_charts,
    plot_box_chart,
    plot_box_charts_grid,
    plot_radar_chart,
)
from evaluation.utils import load_jsonl

EVALUATION_RESULTS_DIR = "gpt_evaluation"

logger = logging.getLogger("evaluation")


def send_question_to_target(question: str, url: str, parameters: dict = {}, raise_error=True) -> dict:
    """Send a question to the ask endpoint and return the response."""
    headers = {
        "Content-Type": "application/json",
    }
    body = {
        "messages": [{"content": question, "role": "user"}],
        "context": parameters,
    }

    try:
        r = requests.post(url, headers=headers, json=body)
        r.encoding = "utf-8"
        latency = r.elapsed.total_seconds()

        r.raise_for_status()

        try:
            response_dict = r.json()
        except json.JSONDecodeError:
            raise ValueError(
                f"Response from target {url} is not valid JSON:\n\n{r.text} \n"
                "Make sure that your configuration points at a chat endpoint that returns a single JSON object.\n"
            )
        try:
            answer = response_dict["message"]["content"]
            data_points = response_dict["context"]["data_points"]["text"]
            context = "\n\n".join(data_points)
        except Exception:
            raise ValueError(
                "Response does not adhere to the expected schema. \n"
                "Either adjust the app response or adjust send_question_to_target() to match the actual schema.\n"
                f"Response: {response_dict}"
            )

        response_obj = {"answer": answer, "context": context, "latency": latency}
        return response_obj
    except Exception as e:
        if raise_error:
            raise e
        return {
            "answer": str(e),
            "context": str(e),
            "latency": -1,
        }


def evaluate_row(
    row,
    target_url: str,
    openai_config: dict,
    requested_metrics: list,
    target_parameters: dict = {},
) -> dict:
    """Evaluate a single row of test data."""
    output = {}
    output["question"] = row["question"]
    output["truth"] = row["truth"]
    target_response = send_question_to_target(
        question=row["question"],
        url=target_url,
        parameters=target_parameters,
    )
    output.update(target_response)
    for metric in requested_metrics:
        result = metric.evaluator_fn(openai_config=openai_config)(
            question=row["question"],
            answer=output["answer"],
            context=output["context"],
            ground_truth=row["truth"],
        )
        output.update(result)
    return output


def run_evaluation(
    openai_config: AzureOpenAIModelConfiguration,
    testdata_path: Path,
    results_dir: Path,
    target_url: str,
    passing_rate: int,
    max_workers: int,
    target_parameters: dict,
    requested_metrics: list,
    num_questions: int = None,
):
    """Run evaluation on the provided test data."""
    logger.info("Running evaluation using data from %s", testdata_path)
    testdata = load_jsonl(testdata_path)
    if num_questions:
        logger.info("Limiting evaluation to %s questions", num_questions)
        testdata = testdata[:num_questions]

    logger.info("Starting evaluation...")
    for metric in requested_metrics:
        if metric not in metrics_by_name:
            logger.error(f"Requested metric {metric} is not available. Available metrics: {metrics_by_name.keys()}")
            return False

    requested_metrics = [
        metrics_by_name[metric_name] for metric_name in requested_metrics if metric_name in metrics_by_name
    ]

    questions_with_ratings = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(evaluate_row, row, target_url, openai_config, requested_metrics, target_parameters): row
            for row in testdata
        }
        for future in track(concurrent.futures.as_completed(futures), description="Processing..."):
            row_result = future.result()
            questions_with_ratings.append(row_result)

    logger.info("Evaluation calls have completed. Calculating overall metrics now...")
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "eval_results.jsonl", "w", encoding="utf-8") as results_file:
        for row in questions_with_ratings:
            results_file.write(json.dumps(row, ensure_ascii=False) + "\n")

    dump_summary(questions_with_ratings, requested_metrics, passing_rate, results_dir)
    plot_diagrams(questions_with_ratings, requested_metrics, passing_rate, results_dir)
    return True


def run_evaluation_from_config(working_dir: Path, config: dict, num_questions: int = None, target_url: str = None):
    """Run evaluation using the provided configuration file."""
    timestamp = int(time.time())
    results_dir = working_dir / config["results_dir"] / EVALUATION_RESULTS_DIR / f"experiment-{timestamp}"
    results_dir.mkdir(parents=True, exist_ok=True)

    openai_config = service_setup.get_openai_config()
    testdata_path = working_dir / config["testdata_path"]

    evaluation_run_complete = run_evaluation(
        openai_config=openai_config,
        testdata_path=testdata_path,
        results_dir=results_dir,
        target_url=os.environ.get("BACKEND_URI") + "/ask" if target_url is None else target_url,
        target_parameters=config.get("target_parameters", {}),
        passing_rate=config.get("passing_rate", 3),
        max_workers=config.get("max_workers", 4),
        num_questions=num_questions,
        requested_metrics=config.get(
            "requested_metrics",
            [
                "gpt_groundedness",
                "gpt_relevance",
                "gpt_coherence",
                "answer_length",
                "latency",
            ],
        ),
    )

    if evaluation_run_complete:
        results_config_path = results_dir / "config.json"
        logger.info("Saving original config file back to %s", results_config_path)

        # Replace relative paths with absolute paths in the original config
        config["testdata_path"] = str(testdata_path)
        config["results_dir"] = str(results_dir)

        # Add extra params to original config
        config["target_url"] = target_url
        config["evaluation_gpt_model"] = openai_config.model

        with open(results_config_path, "w", encoding="utf-8") as output_config:
            output_config.write(json.dumps(config, indent=4))
    else:
        logger.error("Evaluation was terminated early due to an error ⬆")


def dump_summary(rated_questions: dict, requested_metrics: list, passing_rate: float, results_dir: Path):
    """Save evaluation summary to a file."""
    summary = {}
    rated_questions_df = pd.DataFrame(rated_questions)

    for metric in requested_metrics:
        metric_result = metric.get_aggregate_stats(rated_questions_df, passing_rate)
        summary[metric.METRIC_NAME] = metric_result

    with open(results_dir / "summary.json", "w", encoding="utf-8") as summary_file:
        summary_file.write(json.dumps(summary, indent=4))
    logger.info("Evaluation results saved in %s", results_dir)


def plot_diagrams(questions_with_ratings: list, requested_metrics: list, passing_rate: int, results_dir: Path):
    """Summarize the evaluation results and plot them."""
    df = pd.DataFrame(questions_with_ratings)
    rating_stat_data = {
        "pass_count": {},
        "pass_rate": {},
        "mean_rating": {},
    }
    stat_metric_data = {"latency": {}, "f1_score": {}, "answer_length": {}}
    requested_gpt_metrics, requested_stat_metrics = {}, {}
    gpt_metric_data_points, stat_metric_data_points = {}, {}

    width = 0.4  # the width of the bars

    for metric in requested_metrics:
        metric_name = metric.METRIC_NAME
        short_name = metric.SHORT_NAME
        data = df[metric_name].dropna()

        metric_result = metric.get_aggregate_stats(df, passing_rate)
        if issubclass(metric, BuiltinRatingMetric):  # If it's a GPT Rating metric
            requested_gpt_metrics[metric_name] = metric
            if len(data) > 0:
                gpt_metric_data_points[short_name] = data.tolist()
            for stat, value in metric_result.items():
                rating_stat_data[stat][short_name] = value
        else:
            requested_stat_metrics[metric_name] = metric
            if len(data) > 0:
                stat_metric_data_points[short_name] = data.tolist()
            stat_metric_data[short_name] = metric_result

    display_stats_name = {
        "pass_count": "Pass Count",
        "pass_rate": "Pass Rate",
        "mean_rating": "Average Rating",
    }

    stats_y_labels = {
        "pass_count": "Number of Questions",
        "pass_rate": "Percentage",
        "mean_rating": "Rating Score",
    }

    stats_y_lim = {"pass_count": len(questions_with_ratings), "pass_rate": 1.0, "mean_rating": 5.0}

    # Draw the chart for the results
    data = [data for _, data in rating_stat_data.items()]
    titles = [display_stats_name[mn] for mn in rating_stat_data.keys()]
    y_labels = [stats_y_labels[mn] for mn in rating_stat_data.keys()]
    y_lims = [stats_y_lim[mn] for mn in rating_stat_data.keys()]
    layout = (int(np.ceil(len(rating_stat_data) / 3)), 3 if len(rating_stat_data) > 3 else len(rating_stat_data))

    plot_bar_charts(
        layout, data, titles, y_labels, results_dir / "evaluation_results.pdf", y_max_lim=y_lims, width=width
    )

    gpt_metric_avg_ratings = [val for _, val in rating_stat_data["mean_rating"].items()]
    gpt_metric_short_names = [m.SHORT_NAME for _, m in requested_gpt_metrics.items()]
    plot_radar_chart(
        gpt_metric_short_names,
        gpt_metric_avg_ratings,
        "GPT Rating Metrics Results",
        5,
        results_dir / "evaluation_gpt_radar.pdf",
    )

    data = [data for _, data in gpt_metric_data_points.items()]
    labels = list(gpt_metric_data_points.keys())
    plot_box_chart(
        data,
        "GPT Ratings",
        labels,
        "Rating Score",
        results_dir / "evaluation_gpt_boxplot.pdf",
        y_lim=(0.0, 5.0),
    )

    data = [data for _, data in stat_metric_data_points.items()]
    titles = list(stat_metric_data_points.keys())
    y_labels = [metric.NOTE for _, metric in requested_stat_metrics.items()]
    layout = (
        int(np.ceil(len(stat_metric_data_points) / 3)),
        3 if len(stat_metric_data_points) > 3 else len(stat_metric_data_points),
    )

    plot_box_charts_grid(
        layout,
        data,
        titles,
        y_labels,
        results_dir / "evaluation_stat_boxplot.pdf",
    )
