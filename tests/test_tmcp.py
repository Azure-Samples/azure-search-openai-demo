from __future__ import annotations

import json
from pathlib import Path

from tmcp.aggregate import aggregate_findings, discover_inputs
from tmcp.constants import CAP_VALUE, DEFAULT_SEVERITY_WEIGHTS
from tmcp.pa import compute_pa

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "tmcp" / "scans"
EVENT_PAYLOAD = Path(__file__).parent / "fixtures" / "tmcp" / "event.json"
COVERAGE_SUMMARY = Path(__file__).parent / "fixtures" / "tmcp" / "coverage-summary.json"


def test_discover_inputs_handles_directories(tmp_path):
    (tmp_path / "nested").mkdir()
    sample = tmp_path / "nested" / "scan.json"
    sample.write_text("[]", encoding="utf-8")
    files = discover_inputs([str(tmp_path)])
    assert sample in files


def test_aggregate_findings_produces_expected_totals():
    files = sorted(FIXTURE_ROOT.iterdir())
    summary = aggregate_findings(files)
    assert summary["totals"] == {
        "critical": 1,
        "high": 2,
        "medium": 2,
        "low": 1,
        "info": 0,
    }
    assert summary["blockers"] == 1
    assert summary["non_blocker_score"] == 23.0
    assert summary["cap"] == CAP_VALUE
    tools = {scan["tool"] for scan in summary["scans"]}
    assert tools == {"Bandit", "Snyk", "Trivy"}


def test_aggregate_findings_supports_custom_weights(tmp_path):
    files = sorted(FIXTURE_ROOT.iterdir())
    weights = DEFAULT_SEVERITY_WEIGHTS.copy()
    weights.update({"medium": 10})
    summary = aggregate_findings(files, weights=weights)
    # With two medium findings, updating medium weight to 10 yields: 2*10 + 2*8 + 1 = 37
    assert summary["non_blocker_score"] == 37.0
    output = tmp_path / "summary.json"
    output.write_text(json.dumps(summary))
    assert output.exists()


def test_compute_pa_returns_expected_shape():
    files = sorted(FIXTURE_ROOT.iterdir())
    summary = aggregate_findings(files)
    event = json.loads(EVENT_PAYLOAD.read_text())
    coverage = json.loads(COVERAGE_SUMMARY.read_text())
    result = compute_pa(event, summary, coverage)
    assert 0 <= result.process <= 1
    assert 0 <= result.architecture <= 1
    assert result.base == round(result.process * result.architecture, 4)
    assert result.q >= 1
    assert isinstance(result.r_star, float)
