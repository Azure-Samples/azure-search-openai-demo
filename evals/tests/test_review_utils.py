import json
from pathlib import Path

from evaltools.review.diff_markdown import main as diff_markdown_main
from evaltools.review.utils import diff_directories, summarize_results


def write_run(
    results_dir: Path,
    name: str,
    summary: dict,
    results: list[dict],
    parameters: dict | None = None,
):
    """Create a single run folder with summary.json, eval_results.jsonl, and evaluate_parameters.json."""
    folder = results_dir / name
    folder.mkdir(parents=True)
    (folder / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with open(folder / "eval_results.jsonl", "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")
    (folder / "evaluate_parameters.json").write_text(json.dumps(parameters or {}), encoding="utf-8")
    return folder


def test_summarize_results_single_run(tmp_path):
    write_run(
        tmp_path,
        "run1",
        summary={"gpt_relevance": {"mean_rating": 4.5, "pass_rate": 0.9}},
        results=[{"question": "Q1"}, {"question": "Q2"}],
        parameters={"model": "gpt-5.4"},
    )

    rows, row_parameters = summarize_results(tmp_path)

    # With a single run, the metric is shown even though it only appears once.
    assert rows[0] == ["folder", "gpt_relevance", "", "n"]
    assert rows[1][0] == ""
    assert set(rows[1][1:3]) == {"mean_rating", "pass_rate"}
    assert rows[1][3] == "count"
    # The data row starts with the folder name and ends with the question count.
    assert rows[2][0] == "run1"
    assert rows[2][-1] == 2
    assert row_parameters == {"run1": {"model": "gpt-5.4"}}


def test_summarize_results_drops_unshared_metrics(tmp_path):
    # "shared" appears in both runs; "only_in_run1" appears once and must be dropped.
    write_run(
        tmp_path,
        "run1",
        summary={
            "shared": {"mean": 3.0, "rate": 0.5},
            "only_in_run1": {"mean": 1.0},
        },
        results=[{"question": "Q1"}],
    )
    write_run(
        tmp_path,
        "run2",
        summary={"shared": {"mean": 4.0, "rate": 0.7}},
        results=[{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}],
    )

    rows, _ = summarize_results(tmp_path)

    header = rows[0]
    assert "shared" in header
    assert "only_in_run1" not in header
    # Folders are sorted, so run1 comes before run2.
    assert rows[2][0] == "run1"
    assert rows[3][0] == "run2"
    assert rows[2][-1] == 1
    assert rows[3][-1] == 3


def test_summarize_results_missing_stat_uses_placeholder(tmp_path):
    # run2 is missing the metric entirely, so its cells should be "?".
    write_run(
        tmp_path,
        "run1",
        summary={"m": {"mean": 2.0}},
        results=[{"question": "Q1"}],
    )
    write_run(
        tmp_path,
        "run2",
        summary={"m": {"mean": 5.0}, "extra": {"mean": 1.0}},
        results=[{"question": "Q1"}],
    )
    # Force "m" shared and give run2 a metric run1 lacks so the ? path is exercised.
    write_run(
        tmp_path,
        "run3",
        summary={"other": {"mean": 9.0}},
        results=[{"question": "Q1"}],
    )

    rows, _ = summarize_results(tmp_path)
    header = rows[0]
    # "m" is in run1 and run2 (count 2) -> shown; "extra"/"other" appear once -> dropped.
    assert "m" in header
    assert "extra" not in header
    assert "other" not in header
    m_index = header.index("m")
    # run3 has no "m", so it should carry a placeholder.
    run3_row = rows[-1]
    assert run3_row[0] == "run3"
    assert run3_row[m_index] == "?"


def test_diff_directories_no_filter(tmp_path):
    d1 = write_run(tmp_path, "a", summary={}, results=[{"question": "Q1", "score": 1}])
    d2 = write_run(tmp_path, "b", summary={}, results=[{"question": "Q1", "score": 2}])

    data_dicts = diff_directories([d1, d2])

    assert len(data_dicts) == 2
    assert data_dicts[0]["Q1"]["score"] == 1
    assert data_dicts[1]["Q1"]["score"] == 2


def test_diff_directories_changed_filters_equal(tmp_path):
    d1 = write_run(
        tmp_path,
        "a",
        summary={},
        results=[{"question": "same", "score": 3}, {"question": "diff", "score": 3}],
    )
    d2 = write_run(
        tmp_path,
        "b",
        summary={},
        results=[{"question": "same", "score": 3}, {"question": "diff", "score": 4}],
    )

    data_dicts = diff_directories([d1, d2], changed="score")

    # "same" has identical scores -> filtered out of both; "diff" remains.
    assert "same" not in data_dicts[0]
    assert "same" not in data_dicts[1]
    assert "diff" in data_dicts[0]
    assert "diff" in data_dicts[1]


def test_diff_directories_changed_uses_isclose(tmp_path):
    # Floats that are close should be treated as unchanged and filtered.
    d1 = write_run(tmp_path, "a", summary={}, results=[{"question": "Q", "score": 0.1 + 0.2}])
    d2 = write_run(tmp_path, "b", summary={}, results=[{"question": "Q", "score": 0.3}])

    data_dicts = diff_directories([d1, d2], changed="score")

    assert "Q" not in data_dicts[0]


def test_diff_directories_changed_skips_missing_and_none(tmp_path):
    d1 = write_run(
        tmp_path,
        "a",
        summary={},
        results=[
            {"question": "only_in_a", "score": 1},
            {"question": "none_value", "score": None},
            {"question": "kept", "score": 1},
        ],
    )
    d2 = write_run(
        tmp_path,
        "b",
        summary={},
        results=[
            {"question": "none_value", "score": None},
            {"question": "kept", "score": 2},
        ],
    )

    data_dicts = diff_directories([d1, d2], changed="score")

    # Question missing from d2 is dropped from d1.
    assert "only_in_a" not in data_dicts[0]
    # None-valued metric is dropped from d1.
    assert "none_value" not in data_dicts[0]
    # Differing values are kept.
    assert "kept" in data_dicts[0]


def test_diff_markdown_escapes_html(tmp_path):
    # Answer/question/truth containing HTML metacharacters must be escaped.
    d1 = write_run(
        tmp_path,
        "run1",
        summary={},
        results=[
            {
                "question": "What is <b>a & b</b>?",
                "answer": "Use <script>alert(1)</script>",
                "truth": "a & b <tag>",
                "gpt_relevance": 4,
            }
        ],
    )

    markdown = diff_markdown_main([d1])

    assert "<script>" not in markdown
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in markdown
    assert "&amp;" in markdown
    # The legitimate table structure is preserved.
    assert "<table>" in markdown
    assert "<td>" in markdown


def test_diff_markdown_includes_metric_rows(tmp_path):
    d1 = write_run(
        tmp_path,
        "run1",
        summary={},
        results=[{"question": "Q", "answer": "A", "truth": "T", "gpt_relevance": 4.25}],
    )
    d2 = write_run(
        tmp_path,
        "run2",
        summary={},
        results=[{"question": "Q", "answer": "B", "truth": "T", "gpt_relevance": 3.0}],
    )

    markdown = diff_markdown_main([d1, d2])

    # Metric name row is present and float values are rounded to 1 decimal.
    assert "gpt_relevance" in markdown
    assert "4.2" in markdown or "4.3" in markdown
    # A downward arrow is added because run2's value is lower than run1's.
    assert "⬇️" in markdown
