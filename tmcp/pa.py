"""Dynamic computation of TMCP P/A metrics."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import CAP_VALUE, KAPPA

BRANCH_SCORES = {
    "main": 0.95,
    "master": 0.95,
    "release": 1.0,
    "hotfix": 0.9,
    "chore": 0.8,
    "bugfix": 0.85,
    "feature": 0.75,
}
NEGATIVE_LABELS = {"blocked", "needs-work", "wip", "draft"}
POSITIVE_LABELS = {
    "ready": 0.15,
    "qa": 0.15,
    "security": 0.2,
    "documentation": 0.05,
    "tmcp": 0.1,
}


@dataclass
class SignalBundle:
    branch_score: float
    dod_score: float
    label_score: float
    scans_score: float
    low_risk_score: float
    tests_score: float
    coverage_norm: float
    qs: float


@dataclass
class PAResult:
    process: float
    architecture: float
    base: float
    q: float
    qs: float
    nbs: float
    blockers: int
    r_star: float
    summary: dict[str, float]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _branch_score(event: dict[str, Any]) -> float:
    ref = (
        event.get("pull_request", {})
        .get("head", {})
        .get("ref")
        or event.get("ref", "")
    )
    ref = ref.replace("refs/heads/", "")
    for prefix, score in BRANCH_SCORES.items():
        if ref.lower().startswith(prefix):
            return score
    return 0.7


def _dod_score(event: dict[str, Any]) -> float:
    body = event.get("pull_request", {}).get("body") or ""
    total_items = body.count("[ ") + body.count("[\t") + body.count("[x") + body.count("[X")
    completed = body.count("[x") + body.count("[X")
    if total_items == 0:
        return 0.6
    return completed / total_items


def _label_score(event: dict[str, Any]) -> float:
    raw_labels = event.get("pull_request", {}).get("labels", []) or []
    labels = [entry for entry in raw_labels if isinstance(entry, dict)]
    if not labels:
        return 0.6
    score = 0.6
    for entry in labels:
        name = entry.get("name", "").lower()
        for label, delta in POSITIVE_LABELS.items():
            if label in name:
                score += delta
        for negative in NEGATIVE_LABELS:
            if negative in name:
                score -= 0.2
    return max(0.0, min(1.0, score))


def _scan_metrics(summary: dict[str, Any]) -> tuple[float, float, float, int, float]:
    totals = summary.get("totals", {})
    total_findings = sum(totals.values()) or 0
    low_risk = (
        (totals.get("low", 0) + totals.get("info", 0)) / total_findings
        if total_findings
        else 1.0
    )
    nbs = float(summary.get("non_blocker_score", 0.0))
    cap = float(summary.get("cap", CAP_VALUE)) or CAP_VALUE
    blockers = int(summary.get("blockers", 0))
    risk_ratio = min(1.0, nbs / cap) if cap else 1.0
    blocker_penalty = min(1.0, blockers * 0.25)
    scans_score = max(0.0, 1.0 - (0.7 * risk_ratio + 0.3 * blocker_penalty))
    coverage_norm = summary.get("quality", {}).get("coverage_norm")
    return scans_score, low_risk, nbs, blockers, coverage_norm if coverage_norm is not None else -1


def _coverage_metrics(coverage: dict[str, Any]) -> tuple[float, float]:
    total = coverage.get("total", {})
    lines = total.get("lines", {}).get("pct")
    statements = total.get("statements", {}).get("pct")
    metric = lines or statements
    coverage_norm = (metric / 100.0) if metric is not None else 0.8
    tests = coverage.get("tests")
    if isinstance(tests, dict) and tests.get("total"):
        tests_score = tests.get("passed", 0) / tests.get("total")
    else:
        tests_score = coverage_norm
    return min(1.0, max(0.0, tests_score)), min(1.0, max(0.0, coverage_norm))


def compute_signals(
    event: dict[str, Any],
    summary: dict[str, Any],
    coverage: dict[str, Any],
) -> SignalBundle:
    branch_score = _branch_score(event)
    dod_score = _dod_score(event)
    label_score = _label_score(event)
    scans_score, low_risk, nbs, blockers, coverage_norm_from_summary = _scan_metrics(summary)
    tests_score, coverage_norm = _coverage_metrics(coverage)
    if coverage_norm_from_summary and coverage_norm_from_summary > 0:
        coverage_norm = coverage_norm_from_summary
    tests_combined = (tests_score + coverage_norm) / 2
    qs = min(1.0, (coverage_norm + tests_score + low_risk + scans_score) / 4)
    return SignalBundle(
        branch_score=branch_score,
        dod_score=dod_score,
        label_score=label_score,
        scans_score=scans_score,
        low_risk_score=low_risk,
        tests_score=tests_combined,
        coverage_norm=coverage_norm,
        qs=qs,
    )


def compute_pa(
    event: dict[str, Any],
    summary: dict[str, Any],
    coverage: dict[str, Any],
) -> PAResult:
    signals = compute_signals(event, summary, coverage)
    process = (
        0.34 * signals.branch_score
        + 0.33 * signals.dod_score
        + 0.33 * signals.label_score
    )
    architecture = (
        0.4 * signals.scans_score
        + 0.2 * signals.low_risk_score
        + 0.4 * signals.tests_score
    )
    base = process * architecture
    qs = signals.qs
    q = 1.0 + qs
    nbs = float(summary.get("non_blocker_score", 0.0))
    blockers = int(summary.get("blockers", 0))
    r_star = (base ** q) - (nbs / CAP_VALUE) - (KAPPA * blockers)
    result = {
        "branch": signals.branch_score,
        "dod": signals.dod_score,
        "labels": signals.label_score,
        "scans": signals.scans_score,
        "low_risk": signals.low_risk_score,
        "tests_plus_coverage": signals.tests_score,
        "coverage_norm": signals.coverage_norm,
    }
    return PAResult(
        process=round(process, 3),
        architecture=round(architecture, 3),
        base=round(base, 4),
        q=round(q, 3),
        qs=round(qs, 3),
        nbs=round(nbs, 2),
        blockers=blockers,
        r_star=round(r_star, 3),
        summary=result,
    )


def _gate_summary(result: PAResult) -> dict[str, dict[str, float | bool]]:
    gates = {
        "base": {
            "value": result.base,
            "threshold": 0.75,
            "passed": result.base >= 0.75,
        },
        "q": {
            "value": result.q,
            "threshold": 1.2,
            "passed": result.q >= 1.2,
        },
        "r_star": {
            "value": result.r_star,
            "threshold": 0.10,
            "passed": result.r_star >= 0.10,
        },
        "blockers": {
            "value": result.blockers,
            "threshold": 0,
            "passed": result.blockers == 0,
        },
    }
    return gates


def _format_json(
    result: PAResult,
    gates: dict[str, dict[str, float | bool]],
) -> dict[str, Any]:
    return {
        "process": result.process,
        "architecture": result.architecture,
        "base": result.base,
        "q": result.q,
        "qs": result.qs,
        "nbs": result.nbs,
        "blockers": result.blockers,
        "r_star": result.r_star,
        "signals": result.summary,
        "gates": gates,
    }


def cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute dynamic P/A values for TMCP")
    parser.add_argument("--event", required=True, help="Path to the GitHub event payload JSON.")
    parser.add_argument("--summary", required=True, help="Path to TMCP summary.json")
    parser.add_argument(
        "--coverage",
        default="coverage/coverage-summary.json",
        help="Path to coverage summary JSON (default coverage/coverage-summary.json)",
    )
    parser.add_argument(
        "--output",
        default="pa.json",
        help="Where to write the computed values.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with non-zero exit code when gates are not satisfied.",
    )
    args = parser.parse_args(argv)
    event = _load_json(Path(args.event))
    summary = _load_json(Path(args.summary))
    coverage = _load_json(Path(args.coverage))
    result = compute_pa(event, summary, coverage)
    gates = _gate_summary(result)
    payload = _format_json(result, gates)
    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    status = all(gate["passed"] for gate in gates.values())
    print(json.dumps(payload, indent=2))
    if args.strict and not status:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli())
