import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

DEFAULT_BOOTSTRAP_ITERATIONS = 5000
DEFAULT_PERMUTATION_ITERATIONS = 10000
DEFAULT_RANDOM_SEED = 0
DEFAULT_ALPHA = 0.05
PASSING_SCORE = 4


def groundedness_pass_value(row: dict[str, Any]) -> float:
    score = row.get("gpt_groundedness", row.get("groundedness"))
    return 1.0 if score is not None and float(score) >= PASSING_SCORE else 0.0


def relevance_pass_value(row: dict[str, Any]) -> float:
    score = row.get("gpt_relevance", row.get("relevance"))
    return 1.0 if score is not None and float(score) >= PASSING_SCORE else 0.0


METRIC_EXTRACTORS: dict[str, Any] = {
    "gpt_groundedness.pass_rate": groundedness_pass_value,
    "gpt_groundedness.mean_rating": lambda row: float(row["gpt_groundedness"]),
    "gpt_relevance.pass_rate": relevance_pass_value,
    "gpt_relevance.mean_rating": lambda row: float(row["gpt_relevance"]),
    "answer_length.mean": lambda row: float(row["answer_length"]),
    "latency.mean": lambda row: float(row["latency"]),
    "citations_matched.rate": lambda row: float(row["citations_matched"]),
    "any_citation.rate": lambda row: 1.0 if row["any_citation"] else 0.0,
}


@dataclass
class RunData:
    name: str
    path: Path
    config: dict[str, Any]
    rows_by_question: dict[str, dict[str, Any]]


@dataclass
class MetricSummary:
    metric: str
    mean: float
    ci_low: float
    ci_high: float
    sample_size: int


@dataclass
class GroupSummary:
    label: str
    run_count: int
    run_names: list[str]
    run_paths: list[str]
    question_count: int
    config_consistent: bool
    testdata_paths: list[str]
    metrics: list[MetricSummary]
    question_metric_values: dict[str, dict[str, float]]


@dataclass
class MetricComparison:
    metric: str
    baseline_mean: float
    candidate_mean: float
    delta_mean: float
    ci_low: float
    ci_high: float
    p_value: float
    significant: bool
    paired_questions: int


def canonicalize_config(config: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(config))
    normalized.pop("results_dir", None)
    return json.dumps(normalized, sort_keys=True)


def load_run(path: Path) -> RunData:
    config = json.loads((path / "config.json").read_text())
    rows_by_question: dict[str, dict[str, Any]] = {}
    for line in (path / "eval_results.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        question = str(row["question"])
        rows_by_question[question] = row
    return RunData(name=path.name, path=path, config=config, rows_by_question=rows_by_question)


def mean_confidence_interval(values: list[float], iterations: int, seed: int) -> tuple[float, float]:
    if not values:
        raise ValueError("Cannot compute a confidence interval for an empty sample")
    if len(values) == 1:
        return values[0], values[0]

    rng = random.Random(seed)
    sample_size = len(values)
    bootstrap_means: list[float] = []
    for _ in range(iterations):
        bootstrap_sample = [values[rng.randrange(sample_size)] for _ in range(sample_size)]
        bootstrap_means.append(fmean(bootstrap_sample))
    bootstrap_means.sort()
    return percentile_bounds(bootstrap_means)


def percentile_bounds(sorted_values: list[float], confidence_level: float = 0.95) -> tuple[float, float]:
    lower_fraction = (1 - confidence_level) / 2
    upper_fraction = 1 - lower_fraction
    lower_index = max(0, math.floor(lower_fraction * (len(sorted_values) - 1)))
    upper_index = min(len(sorted_values) - 1, math.ceil(upper_fraction * (len(sorted_values) - 1)))
    return sorted_values[lower_index], sorted_values[upper_index]


def paired_permutation_p_value(deltas: list[float], iterations: int, seed: int) -> float:
    if not deltas:
        raise ValueError("Cannot compute significance for an empty sample")
    observed = abs(fmean(deltas))
    sample_size = len(deltas)

    if sample_size <= 16:
        extreme = 0
        total = 1 << sample_size
        for mask in range(total):
            signed = [delta if (mask >> index) & 1 else -delta for index, delta in enumerate(deltas)]
            if abs(fmean(signed)) >= observed:
                extreme += 1
        return extreme / total

    rng = random.Random(seed)
    extreme = 0
    for _ in range(iterations):
        signed = [delta if rng.random() >= 0.5 else -delta for delta in deltas]
        if abs(fmean(signed)) >= observed:
            extreme += 1
    return extreme / iterations


def build_group_summary(label: str, run_paths: list[Path], iterations: int, seed: int) -> GroupSummary:
    runs = [load_run(path) for path in run_paths]
    if not runs:
        raise ValueError(f"Group '{label}' has no runs")

    shared_questions = set(runs[0].rows_by_question)
    for run in runs[1:]:
        shared_questions &= set(run.rows_by_question)
    sorted_questions = sorted(shared_questions)

    config_signatures = {canonicalize_config(run.config) for run in runs}
    testdata_paths = sorted({str(run.config.get("testdata_path", "")) for run in runs})

    question_metric_values: dict[str, dict[str, float]] = {metric: {} for metric in METRIC_EXTRACTORS}
    metric_summaries: list[MetricSummary] = []

    for metric, extractor in METRIC_EXTRACTORS.items():
        per_question_values: dict[str, float] = {}
        for question in sorted_questions:
            values = [float(extractor(run.rows_by_question[question])) for run in runs]
            per_question_values[question] = fmean(values)

        metric_values = list(per_question_values.values())
        mean_value = fmean(metric_values) if metric_values else math.nan
        ci_low, ci_high = (
            mean_confidence_interval(metric_values, iterations, seed) if metric_values else (math.nan, math.nan)
        )
        metric_summaries.append(
            MetricSummary(
                metric=metric,
                mean=mean_value,
                ci_low=ci_low,
                ci_high=ci_high,
                sample_size=len(metric_values),
            )
        )
        question_metric_values[metric] = per_question_values

    return GroupSummary(
        label=label,
        run_count=len(runs),
        run_names=[run.name for run in runs],
        run_paths=[str(run.path) for run in runs],
        question_count=len(sorted_questions),
        config_consistent=len(config_signatures) == 1,
        testdata_paths=testdata_paths,
        metrics=metric_summaries,
        question_metric_values=question_metric_values,
    )


def compare_groups(
    baseline: GroupSummary,
    candidate: GroupSummary,
    iterations: int,
    seed: int,
    alpha: float,
) -> list[MetricComparison]:
    comparisons: list[MetricComparison] = []
    baseline_metrics = {metric.metric: metric for metric in baseline.metrics}
    candidate_metrics = {metric.metric: metric for metric in candidate.metrics}

    for metric_name in METRIC_EXTRACTORS:
        baseline_values = baseline.question_metric_values[metric_name]
        candidate_values = candidate.question_metric_values[metric_name]
        shared_questions = sorted(set(baseline_values) & set(candidate_values))
        deltas = [candidate_values[question] - baseline_values[question] for question in shared_questions]
        ci_low, ci_high = mean_confidence_interval(deltas, iterations, seed) if deltas else (math.nan, math.nan)
        p_value = paired_permutation_p_value(deltas, iterations, seed) if deltas else math.nan
        comparisons.append(
            MetricComparison(
                metric=metric_name,
                baseline_mean=baseline_metrics[metric_name].mean,
                candidate_mean=candidate_metrics[metric_name].mean,
                delta_mean=fmean(deltas) if deltas else math.nan,
                ci_low=ci_low,
                ci_high=ci_high,
                p_value=p_value,
                significant=bool(not math.isnan(p_value) and p_value < alpha),
                paired_questions=len(shared_questions),
            )
        )
    return comparisons


def parse_group_argument(group_argument: str) -> tuple[str, list[Path]]:
    if "=" not in group_argument:
        raise ValueError(f"Invalid group '{group_argument}'. Expected label=dir1,dir2")
    label, raw_paths = group_argument.split("=", 1)
    paths = [Path(path.strip()) for path in raw_paths.split(",") if path.strip()]
    if not label or not paths:
        raise ValueError(f"Invalid group '{group_argument}'. Expected label=dir1,dir2")
    return label, paths


def resolve_groups(group_arguments: list[str] | None, result_dirs: list[str]) -> list[tuple[str, list[Path]]]:
    if group_arguments:
        return [parse_group_argument(argument) for argument in group_arguments]
    return [(Path(path).name, [Path(path)]) for path in result_dirs]


def render_markdown(
    group_summaries: list[GroupSummary], comparisons_by_label: dict[str, list[MetricComparison]]
) -> str:
    lines = ["# Eval Comparison Summary", "", "## Group Summary", ""]
    lines.append("| Group | Runs | Questions | Config consistent | Test data |")
    lines.append("|---|---:|---:|---|---|")
    for group in group_summaries:
        lines.append(
            f"| {group.label} | {group.run_count} | {group.question_count} | {group.config_consistent} | {', '.join(group.testdata_paths)} |"
        )

    lines.extend(["", "## Metrics", "", "| Group | Metric | Mean | 95% CI | n |", "|---|---|---:|---|---:|"])
    for group in group_summaries:
        for metric in group.metrics:
            lines.append(
                f"| {group.label} | {metric.metric} | {metric.mean:.4f} | [{metric.ci_low:.4f}, {metric.ci_high:.4f}] | {metric.sample_size} |"
            )

    if comparisons_by_label:
        lines.extend(
            [
                "",
                "## Comparisons Vs Reference",
                "",
                "| Candidate | Metric | Baseline mean | Candidate mean | Delta | 95% CI for delta | p-value | Significant | Paired questions |",
                "|---|---|---:|---:|---:|---|---:|---|---:|",
            ]
        )
        for label, comparisons in comparisons_by_label.items():
            for comparison in comparisons:
                lines.append(
                    f"| {label} | {comparison.metric} | {comparison.baseline_mean:.4f} | {comparison.candidate_mean:.4f} | {comparison.delta_mean:.4f} | [{comparison.ci_low:.4f}, {comparison.ci_high:.4f}] | {comparison.p_value:.4f} | {comparison.significant} | {comparison.paired_questions} |"
                )

    return "\n".join(lines)


def build_json_payload(
    group_summaries: list[GroupSummary], comparisons_by_label: dict[str, list[MetricComparison]]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "groups": [
            {
                "label": group.label,
                "run_count": group.run_count,
                "run_names": group.run_names,
                "run_paths": group.run_paths,
                "question_count": group.question_count,
                "config_consistent": group.config_consistent,
                "testdata_paths": group.testdata_paths,
                "metrics": [
                    {
                        "metric": metric.metric,
                        "mean": metric.mean,
                        "ci_low": metric.ci_low,
                        "ci_high": metric.ci_high,
                        "sample_size": metric.sample_size,
                    }
                    for metric in group.metrics
                ],
                "question_metric_values": group.question_metric_values,
            }
            for group in group_summaries
        ],
    }

    if comparisons_by_label:
        payload["comparisons"] = {
            label: [
                {
                    "metric": comparison.metric,
                    "baseline_mean": comparison.baseline_mean,
                    "candidate_mean": comparison.candidate_mean,
                    "delta_mean": comparison.delta_mean,
                    "ci_low": comparison.ci_low,
                    "ci_high": comparison.ci_high,
                    "p_value": comparison.p_value,
                    "significant": comparison.significant,
                    "paired_questions": comparison.paired_questions,
                }
                for comparison in comparisons
            ]
            for label, comparisons in comparisons_by_label.items()
        }

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare eval result folders using averages, bootstrap confidence intervals, and paired significance tests."
    )
    parser.add_argument("result_dirs", nargs="*", help="Result folders to compare if --group is not supplied")
    parser.add_argument(
        "--group",
        action="append",
        help="Group runs by label, e.g. baseline=evals/results/baseline,evals/results/experiment123",
    )
    parser.add_argument(
        "--reference", help="Reference group label for pairwise comparisons. Defaults to the first group"
    )
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, help="Optional path to write the report")
    parser.add_argument("--bootstrap-iterations", type=int, default=DEFAULT_BOOTSTRAP_ITERATIONS)
    parser.add_argument("--permutation-iterations", type=int, default=DEFAULT_PERMUTATION_ITERATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    args = parser.parse_args()

    groups = resolve_groups(args.group, args.result_dirs)
    if not groups:
        raise SystemExit("Provide at least one results directory or one --group argument")

    group_summaries = [
        build_group_summary(label, paths, iterations=args.bootstrap_iterations, seed=args.seed)
        for label, paths in groups
    ]
    group_summary_by_label = {group.label: group for group in group_summaries}

    reference_label = args.reference or group_summaries[0].label
    if reference_label not in group_summary_by_label:
        raise SystemExit(f"Unknown reference group: {reference_label}")

    reference_group = group_summary_by_label[reference_label]
    comparisons_by_label = {
        group.label: compare_groups(
            reference_group,
            group,
            iterations=args.bootstrap_iterations,
            seed=args.seed,
            alpha=args.alpha,
        )
        for group in group_summaries
        if group.label != reference_label
    }

    if args.format == "json":
        output_text = json.dumps(build_json_payload(group_summaries, comparisons_by_label), indent=2)
    else:
        output_text = render_markdown(group_summaries, comparisons_by_label)

    if args.output:
        args.output.write_text(output_text + "\n")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
