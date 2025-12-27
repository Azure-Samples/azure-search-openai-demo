"""Compose TMCP gate summary comments for GitHub pull requests."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

GREEN = "🟢"
YELLOW = "🟡"
RED = "🔴"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def emoji_gate(passed: bool) -> str:
    return GREEN if passed else RED


def risk_indicator(nbs: float, cap: float) -> tuple[str, float]:
    ratio = 0.0 if cap <= 0 else min(1.0, nbs / cap)
    if ratio <= 0.25:
        return GREEN, ratio
    if ratio <= 0.55:
        return YELLOW, ratio
    return RED, ratio


def build_comment(pa: dict[str, Any], summary: dict[str, Any]) -> str:
    gates = pa.get("gates", {})
    gate_rows: list[str] = []
    for key, label, threshold in (
        ("base", "Base ≥ 0.75", 0.75),
        ("q", "Q ≥ 1.20", 1.20),
        ("r_star", "R* ≥ 0.10", 0.10),
        ("blockers", "Blockers = 0", 0),
    ):
        gate = gates.get(key, {})
        emoji = emoji_gate(bool(gate.get("passed")))
        value = gate.get("value", pa.get(key, "–"))
        display_value = f"{value:.3f}" if isinstance(value, (int, float)) else value
        gate_rows.append(f"| {label} | {emoji} | {display_value} | {threshold} |")
    risk_emoji, _ = risk_indicator(pa.get("nbs", 0.0), summary.get("cap", 20))
    overall = GREEN if all(g.get("passed") for g in gates.values()) else RED
    verdict = "APPROVE" if overall == GREEN else "REJECT"
    findings = summary.get("totals", {})
    total_findings = sum(findings.values())
    comment_lines: list[str] = [
            "<!-- tmcp-v2.4 -->",
        "### TMCP v2.4 Gate Summary",
        "",
        "| Gate | Status | Value | Threshold |",
        "| --- | --- | --- | --- |",
        *gate_rows,
        "",
        f"**Risk:** {risk_emoji} (NBS {pa.get('nbs', 0):.2f} / CAP {summary.get('cap', 20)})",
        f"**Verdict:** {overall} **{verdict}**",
        "",
        "<details><summary>Signals & Inputs</summary>",
        "",
        f"- Process (P): `{pa.get('process', 0):.3f}`",
        f"- Architecture (A): `{pa.get('architecture', 0):.3f}`",
        f"- Base: `{pa.get('base', 0):.3f}`",
        f"- Qs: `{pa.get('qs', 0):.3f}` → Q `{pa.get('q', 0):.3f}`",
        f"- R*: `{pa.get('r_star', 0):.3f}`",
        f"- Blockers: `{pa.get('blockers', 0)}`",
        f"- Findings aggregated: `{total_findings}`",
        "",
        "</details>",
        "",
        "_Formula: R* = (P × A)^Q − (NBS / CAP) − κ · Blockers_",
    ]
    return "\n".join(comment_lines)


def write_output(comment: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(comment + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(comment + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format TMCP PR summary comment")
    parser.add_argument("--pa", required=True, help="Path to pa.json produced by tmcp_compute_pa.py")
    parser.add_argument("--summary", required=True, help="Path to tmcp_summary.json")
    parser.add_argument("--out", default="tmcp_comment.md", help="Where to write the markdown comment")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pa = load_json(Path(args.pa))
    summary = load_json(Path(args.summary))
    comment = build_comment(pa, summary)
    write_output(comment, Path(args.out))
    print(comment)


if __name__ == "__main__":
    main()
