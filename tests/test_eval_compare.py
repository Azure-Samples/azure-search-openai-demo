import json
from pathlib import Path

from scripts.eval_compare import build_group_summary, build_json_payload, compare_groups


def write_run(tmp_path: Path, name: str, rows: list[dict], config: dict) -> Path:
    run_dir = tmp_path / name
    run_dir.mkdir()
    (run_dir / "config.json").write_text(json.dumps(config))
    (run_dir / "summary.json").write_text("{}")
    (run_dir / "eval_results.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return run_dir


def make_row(question: str, *, groundedness: float, relevance: float, latency: float, citations: float) -> dict:
    return {
        "question": question,
        "gpt_groundedness": groundedness,
        "groundedness_result": "pass" if groundedness >= 3 else "fail",
        "groundedness_threshold": 3,
        "gpt_relevance": relevance,
        "relevance_result": "pass" if relevance >= 3 else "fail",
        "relevance_threshold": 3,
        "answer_length": 100 + int(groundedness * 10),
        "latency": latency,
        "citations_matched": citations,
        "any_citation": citations > 0,
    }


def test_build_group_summary_averages_repeated_runs(tmp_path: Path) -> None:
    config = {"testdata_path": "ground_truth.jsonl", "target_parameters": {"overrides": {"top": 5}}}
    run_a = write_run(
        tmp_path,
        "run_a",
        [
            make_row("q1", groundedness=5, relevance=4, latency=1.0, citations=1.0),
            make_row("q2", groundedness=3, relevance=5, latency=2.0, citations=0.0),
        ],
        config,
    )
    run_b = write_run(
        tmp_path,
        "run_b",
        [
            make_row("q1", groundedness=4, relevance=4, latency=1.5, citations=1.0),
            make_row("q2", groundedness=5, relevance=5, latency=2.5, citations=1.0),
        ],
        config,
    )

    summary = build_group_summary("baseline", [run_a, run_b], iterations=200, seed=0)

    metrics = {metric.metric: metric for metric in summary.metrics}
    assert summary.run_count == 2
    assert summary.run_names == ["run_a", "run_b"]
    assert summary.question_count == 2
    assert summary.config_consistent is True
    assert metrics["gpt_groundedness.mean_rating"].mean == 4.25
    assert metrics["gpt_groundedness.pass_rate"].mean == 0.75
    assert metrics["citations_matched.rate"].mean == 0.75
    assert summary.question_metric_values["gpt_groundedness.mean_rating"] == {"q1": 4.5, "q2": 4.0}
    assert summary.question_metric_values["gpt_groundedness.pass_rate"] == {"q1": 1.0, "q2": 0.5}
    assert metrics["latency.mean"].ci_low <= metrics["latency.mean"].mean <= metrics["latency.mean"].ci_high


def test_build_json_payload_includes_per_question_grouped_values(tmp_path: Path) -> None:
    config = {"testdata_path": "ground_truth.jsonl", "target_parameters": {"overrides": {"top": 5}}}
    run_a = write_run(
        tmp_path,
        "run_a",
        [
            make_row("q1", groundedness=5, relevance=4, latency=1.0, citations=1.0),
            make_row("q2", groundedness=3, relevance=5, latency=2.0, citations=0.0),
        ],
        config,
    )
    run_b = write_run(
        tmp_path,
        "run_b",
        [
            make_row("q1", groundedness=4, relevance=4, latency=1.5, citations=1.0),
            make_row("q2", groundedness=5, relevance=5, latency=2.5, citations=1.0),
        ],
        config,
    )

    summary = build_group_summary("baseline", [run_a, run_b], iterations=200, seed=0)
    payload = build_json_payload([summary], {})

    group_payload = payload["groups"][0]
    assert group_payload["question_metric_values"]["gpt_groundedness.mean_rating"] == {"q1": 4.5, "q2": 4.0}
    assert group_payload["question_metric_values"]["latency.mean"] == {"q1": 1.25, "q2": 2.25}
    assert "comparisons" not in payload


def test_compare_groups_reports_significance_for_consistent_improvement(tmp_path: Path) -> None:
    config = {"testdata_path": "ground_truth.jsonl", "target_parameters": {"overrides": {"top": 5}}}
    baseline_rows = [
        make_row(f"q{index}", groundedness=3, relevance=3, latency=5.0, citations=0.0) for index in range(10)
    ]
    candidate_rows = [
        make_row(f"q{index}", groundedness=5, relevance=5, latency=4.0, citations=1.0) for index in range(10)
    ]

    baseline_run = write_run(tmp_path, "baseline_run", baseline_rows, config)
    candidate_run = write_run(tmp_path, "candidate_run", candidate_rows, config)

    baseline_summary = build_group_summary("baseline", [baseline_run], iterations=200, seed=0)
    candidate_summary = build_group_summary("candidate", [candidate_run], iterations=200, seed=0)
    comparisons = compare_groups(baseline_summary, candidate_summary, iterations=200, seed=0, alpha=0.05)

    by_metric = {comparison.metric: comparison for comparison in comparisons}
    groundedness = by_metric["gpt_groundedness.mean_rating"]
    latency = by_metric["latency.mean"]

    assert groundedness.delta_mean == 2.0
    assert groundedness.significant is True
    assert groundedness.p_value < 0.01
    assert groundedness.ci_low <= groundedness.delta_mean <= groundedness.ci_high
    assert latency.delta_mean == -1.0
    assert latency.significant is True
