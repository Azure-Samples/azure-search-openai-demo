import concurrent.futures
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from promptflow.core import AzureOpenAIModelConfiguration
from rich.progress import track

from evaluation import service_setup
from evaluation.evaluate_metrics import metrics_by_name
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

    summarize_results_and_plot(questions_with_ratings, requested_metrics, results_dir, passing_rate)
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


def summarize_results_and_plot(
    questions_with_ratings: list, requested_metrics: list, results_dir: Path, passing_rate: int
):
    """Summarize the evaluation results and plot them."""
    df = pd.DataFrame(questions_with_ratings)
    summary = {}
    metric_list, metric_name = [], []
    pass_rate, mean_rate = [], []
    min_list, mean_list, max_list = [], [], []
    for metric in requested_metrics:
        metric_result = metric.get_aggregate_stats(df, passing_rate)
        summary[metric.METRIC_NAME] = metric_result
        if (
            metric.METRIC_NAME == "gpt_groundedness"
            or metric.METRIC_NAME == "gpt_relevance"
            or metric.METRIC_NAME == "gpt_coherence"
            or metric.METRIC_NAME == "gpt_similarity"
            or metric.METRIC_NAME == "gpt_fluency"
        ):
            metric_list.append(metric.METRIC_NAME)
            pass_rate.append(metric_result.get("pass_rate"))
            mean_rate.append(metric_result.get("mean_rating"))
        if metric.METRIC_NAME == "latency" or metric.METRIC_NAME == "f1_score" or metric.METRIC_NAME == "answer_length":
            metric_name.append(metric.METRIC_NAME)
            max = metric_result.get("max")
            min = metric_result.get("min")
            mean = metric_result.get("mean")
            max_list.append(max)
            min_list.append(min)
            mean_list.append(mean)

    # Summary statistics
    with open(results_dir / "summary.json", "w", encoding="utf-8") as summary_file:
        summary_file.write(json.dumps(summary, indent=4))
    logger.info("Evaluation results saved in %s", results_dir)

    # Draw the chart for the results
    fig, ax1 = plt.subplots()
    ax1.bar(metric_list, pass_rate)

    ax1.set_ylabel("passing rate")
    ax1.set_title("Passing rate of evaluation metrics")
    plt.savefig(results_dir / "passing_rate.png")
    plt.close(fig)

    fig, ax2 = plt.subplots()
    ax2.bar(metric_list, mean_rate)

    ax2.set_ylabel("mean score")
    ax2.set_title("Mean score of evaluation metrics")
    plt.savefig(results_dir / "mean_score.png")
    plt.close(fig)

    means = {
        "Max": tuple(max_list),
        "Min": tuple(min_list),
        "Mean": tuple(mean_list),
    }

    x = np.arange(len(metric_name))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 0
    fig, ax3 = plt.subplots(layout="constrained")

    for attribute, measurement in means.items():
        offset = width * multiplier
        rects = ax3.bar(x + offset, measurement, width, label=attribute)
        ax3.bar_label(rects, padding=3)
        multiplier += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax3.set_title("Evaluation results")
    ax3.set_xticks(x + width, tuple(metric_name))
    ax3.legend(loc="upper left", ncols=3)
    ax3.set_ylim(0, 250)

    plt.savefig(results_dir / "eval.png")
    plt.close(fig)
