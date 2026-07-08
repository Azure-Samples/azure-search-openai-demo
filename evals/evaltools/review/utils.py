import json
import math
import os
from pathlib import Path


def summarize_results(results_dir):
    run_summaries = {}
    # first find the shared metrics across the runs
    metric_counts = {}

    folders = [f for f in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, f))]
    folders.sort()
    for folder in folders:
        with open(Path(results_dir) / folder / "summary.json", encoding="utf-8") as f:
            summary = json.load(f)
            run_summaries[folder] = summary
            # first find the common parameters across the runs
            for metric_name in summary:
                metric_counts[metric_name] = metric_counts.get(metric_name, 0) + 1

    # Only show metrics that have shown up at least twice across runs
    shared_metric_names = [
        metric_name for metric_name, count in metric_counts.items() if count > 1 or len(run_summaries) == 1
    ]
    shared_metric_stats = {metric_name: set() for metric_name in shared_metric_names}

    # Now figure out what stat to show about each metric
    for folder, summary in run_summaries.items():
        for metric_name in shared_metric_names:
            if metric_name in summary:
                metric = summary[metric_name]
                if "mean_rating" in metric:
                    shared_metric_stats[metric_name].add("mean_rating")
                elif "mean" in metric:
                    shared_metric_stats[metric_name].add("mean")
                if "pass_rate" in metric:
                    shared_metric_stats[metric_name].add("pass_rate")
                elif "rate" in metric:
                    shared_metric_stats[metric_name].add("rate")

    first_row = ["folder"]
    # Build second row
    second_row = [""]
    for metric_name in shared_metric_names:
        # The first row of columns should have metric name followed by blank column for each stat above 1 stat
        first_row.append(metric_name)
        if len(shared_metric_stats[metric_name]) > 1:
            first_row.extend([""] * (len(shared_metric_stats[metric_name]) - 1))
        # The second row of columns should just have the stat names
        for stat in shared_metric_stats[metric_name]:
            second_row.append(stat)

    rows = [first_row, second_row]
    row_parameters = {}
    # Build rest of the rows
    for folder, summary in run_summaries.items():
        run_row = [folder]
        for metric_name in shared_metric_names:
            for stat in shared_metric_stats[metric_name]:
                if stat in summary.get(metric_name, {}):
                    run_row.append(summary[metric_name][stat])
                else:
                    run_row.append("?")
        with open(Path(results_dir) / folder / "eval_results.jsonl", encoding="utf-8") as f:
            run_row.append(sum(1 for _ in f))
        rows.append(run_row)
        with open(Path(results_dir) / folder / "evaluate_parameters.json", encoding="utf-8") as f:
            row_parameters[folder] = json.load(f)

    return rows, row_parameters


def diff_directories(directories: list[Path], changed: str | None = None):
    data_dicts = []
    for directory in directories:
        with open(directory / "eval_results.jsonl", encoding="utf-8") as f:
            data_json = [json.loads(question_json) for question_json in f.readlines()]
            data_dicts.append({question["question"]: question for question in data_json})
    if changed:
        # filter out questions that have the same value for the given column
        for question in list(data_dicts[0].keys()):
            # if question isn't in the second directory, skip
            if question not in data_dicts[1]:
                data_dicts[0].pop(question)
                continue
            # if either metric is None, skip
            if data_dicts[0][question].get(changed) is None or data_dicts[1][question].get(changed) is None:
                data_dicts[0].pop(question)
                continue
            if data_dicts[0][question].get(changed) == data_dicts[1][question].get(changed):
                if math.isclose(data_dicts[0][question].get(changed), data_dicts[1][question].get(changed)):
                    data_dicts[0].pop(question)
                    data_dicts[1].pop(question)
    return data_dicts
