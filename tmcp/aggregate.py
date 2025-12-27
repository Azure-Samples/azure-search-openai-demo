"""Utilities for aggregating scan artifacts into TMCP summary format."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import (
    BLOCKER_SEVERITIES,
    CAP_VALUE,
    DEFAULT_SEVERITY_WEIGHTS,
    SEVERITY_LEVELS,
    TMCP_SUMMARY_VERSION,
)


@dataclass(slots=True)
class Finding:
    """Normalized representation of a security/scanning finding."""

    tool: str
    severity: str
    title: str
    rule_id: str | None = None
    location: str | None = None
    is_blocker: bool = False
    raw: dict[str, Any] | None = field(default=None, repr=False)

    @staticmethod
    def normalize_severity(value: str | None) -> str:
        if not value:
            return "medium"
        value = value.lower().strip()
        if value not in SEVERITY_LEVELS:
            if value in {"error", "severe"}:
                return "high"
            if value in {"warning", "warn"}:
                return "medium"
            if value in {"note", "info", "information"}:
                return "info"
            if value in {"blocker", "critical"}:
                return "critical"
            return "medium"
        return value

    @classmethod
    def from_dict(
        cls,
        tool: str,
        payload: dict[str, Any],
        fallback_level: str | None = None,
    ) -> "Finding":
        severity = cls.normalize_severity(
            payload.get("severity")
            or payload.get("level")
            or payload.get("impact")
            or fallback_level
        )
        is_blocker = bool(
            payload.get("blocker")
            or severity in BLOCKER_SEVERITIES
            or payload.get("is_blocker")
            or payload.get("properties", {}).get("blocker")
        )
        title = (
            payload.get("message")
            or payload.get("shortDescription")
            or payload.get("title")
            or "Finding"
        )
        rule_id = (
            payload.get("ruleId")
            or payload.get("id")
            or payload.get("rule_id")
        )
        location = payload.get("location") or _extract_location(payload)
        return cls(
            tool=tool or "unknown",
            severity=severity,
            title=str(title),
            rule_id=rule_id and str(rule_id),
            location=location,
            is_blocker=is_blocker,
            raw=payload,
        )


def _extract_location(payload: dict[str, Any]) -> str | None:
    locations = payload.get("locations") or payload.get("location")
    if isinstance(locations, list) and locations:
        entry = locations[0]
    else:
        entry = locations or {}
    if isinstance(entry, dict):
        physical = entry.get("physicalLocation") or entry
        if isinstance(physical, dict):
            artifact = physical.get("artifactLocation") or physical
            if isinstance(artifact, dict):
                uri = artifact.get("uri")
                if uri:
                    return str(uri)
            region = physical.get("region")
            if isinstance(region, dict):
                start_line = region.get("startLine")
                if start_line and artifact and isinstance(artifact, dict):
                    uri = artifact.get("uri")
                    if uri:
                        return f"{uri}:{start_line}"
    if isinstance(entry, str):
        return entry
    return None


def discover_inputs(sources: Sequence[str]) -> list[Path]:
    files: list[Path] = []
    for chunk in sources:
        path = Path(chunk)
        if path.is_dir():
            files.extend(sorted(path.rglob("*")))
        else:
            files.extend(Path().glob(chunk))
    filtered = [p for p in files if p.is_file() and not p.name.startswith(".")]
    unique: dict[str, Path] = {}
    for file in filtered:
        unique[file.resolve().as_posix()] = file
    return list(unique.values())


def _parse_sarif(data: dict[str, Any], fallback_tool: str) -> list[Finding]:
    findings: list[Finding] = []
    runs = data.get("runs") or []
    for run in runs:
        tool = (
            run.get("tool", {})
            .get("driver", {})
            .get("name")
            or fallback_tool
        )
        for result in run.get("results", []) or []:
            payload = dict(result)
            properties = payload.get("properties") or {}
            payload.setdefault("severity", properties.get("severity"))
            payload.setdefault("location", payload.get("locations"))
            findings.append(Finding.from_dict(tool, payload))
    return findings


def _parse_generic_list(data: Iterable[Any], tool: str) -> list[Finding]:
    findings: list[Finding] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        payload = dict(entry)
        # Prefer tool name from entry if present (e.g., Trivy, Snyk), else fall back to inferred tool
        local_tool = str(payload.get("tool") or tool)
        findings.append(Finding.from_dict(local_tool, payload))
    return findings


def _flatten_mapping_entries(container: dict[Any, Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for key, value in container.items():
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    enriched = dict(entry)
                    enriched.setdefault("location", str(key))
                    flattened.append(enriched)
        elif isinstance(value, dict):
            enriched = dict(value)
            enriched.setdefault("location", str(key))
            flattened.append(enriched)
    return flattened


def _parse_dependency_report(data: dict[str, Any], fallback_tool: str) -> list[Finding]:
    tool = str(data.get("tool") or fallback_tool or "dependency-scan")
    findings: list[Finding] = []
    dependencies = data.get("dependencies")
    if not isinstance(dependencies, list):
        return findings
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        vulns_obj = dependency.get("vulns") or []
        if not isinstance(vulns_obj, list):
            continue
        name = dependency.get("name")
        version = dependency.get("version")
        for vuln in vulns_obj:
            if not isinstance(vuln, dict):
                continue
            payload: dict[str, Any] = dict(vuln)
            payload.setdefault("severity", vuln.get("severity"))
            payload.setdefault("title", vuln.get("id"))
            payload.setdefault("rule_id", vuln.get("id"))
            location = f"{name}=={version}" if name and version else name
            if location:
                payload.setdefault("location", location)
            findings.append(Finding.from_dict(tool, payload))
    return findings


def parse_scan_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tool_name = path.stem
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        if "runs" in data:
            return _parse_sarif(data, tool_name)
        if "dependencies" in data:
            return _parse_dependency_report(data, tool_name)
        for key in ("results", "findings", "issues", "alerts", "vulnerabilities", "data"):
            if key in data:
                payload = data[key]
                if isinstance(payload, list):
                    candidates = payload
                elif isinstance(payload, dict):
                    candidates = _flatten_mapping_entries(payload)
                else:
                    continue
                return _parse_generic_list(candidates, data.get("tool", tool_name))
    if isinstance(data, list):
        return _parse_generic_list(data, tool_name)
    return []


def aggregate_findings(
    files: Sequence[Path],
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    weights = {**DEFAULT_SEVERITY_WEIGHTS, **(weights or {})}
    findings = [finding for file in files for finding in parse_scan_file(file)]
    grouped: dict[str, dict[str, int]] = {}
    per_tool_samples: dict[str, list[Finding]] = {}
    non_blocker_score = 0.0
    blockers = 0
    for finding in findings:
        stats = grouped.setdefault(finding.tool, {level: 0 for level in SEVERITY_LEVELS})
        stats[finding.severity] = stats.get(finding.severity, 0) + 1
        samples = per_tool_samples.setdefault(finding.tool, [])
        if len(samples) < 3:
            samples.append(finding)
        if finding.is_blocker:
            blockers += 1
        else:
            non_blocker_score += weights.get(finding.severity, 0.0)
    totals = {level: 0 for level in SEVERITY_LEVELS}
    for stats in grouped.values():
        for level, count in stats.items():
            totals[level] = totals.get(level, 0) + count
    response: dict[str, Any] = {
        "version": TMCP_SUMMARY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [str(f) for f in files],
        "scans": [
            {
                "tool": tool,
                "stats": stats,
                "sample_findings": [
                    {
                        "severity": finding.severity,
                        "title": finding.title,
                        "location": finding.location,
                        "rule_id": finding.rule_id,
                        "is_blocker": finding.is_blocker,
                    }
                    for finding in per_tool_samples.get(tool, [])
                ],
            }
            for tool, stats in sorted(grouped.items())
        ],
        "totals": totals,
        "non_blocker_score": round(non_blocker_score, 2),
        "blockers": blockers,
        "weights": weights,
        "cap": CAP_VALUE,
    }
    return response


def save_summary(summary: dict[str, Any], output: Path, weights_output: Path | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if weights_output:
        weights_output.parent.mkdir(parents=True, exist_ok=True)
        weights_output.write_text(
            json.dumps(
                {
                    "version": summary.get("version"),
                    "weights": summary.get("weights"),
                    "generated_at": summary.get("generated_at"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def _parse_metadata(metadata: Sequence[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in metadata or []:
        if "=" in entry:
            key, value = entry.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate scanner outputs into TMCP summary.json")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["tmcp/scans"],
        help="Directories or glob patterns with scan artifacts.",
    )
    parser.add_argument(
        "--output",
        default="summary.json",
        help="Path to write the aggregated summary JSON.",
    )
    parser.add_argument(
        "--weights-output",
        default="weights_used.json",
        help="Optional path for persisting the weights snapshot.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        help="Optional key=value metadata to embed in the summary.",
    )
    parser.add_argument(
        "--weights",
        help="Optional JSON file overriding severity weights.",
    )
    parsed = parser.parse_args(argv)
    overrides = {}
    if parsed.weights:
        weight_path = Path(parsed.weights)
        if weight_path.exists():
            overrides = json.loads(weight_path.read_text(encoding="utf-8"))
    files = discover_inputs(parsed.sources)
    summary = aggregate_findings(files, weights=overrides)
    if metadata := _parse_metadata(parsed.metadata):
        summary["metadata"] = metadata
    save_summary(
        summary,
        Path(parsed.output),
        Path(parsed.weights_output) if parsed.weights_output else None,
    )
    print(f"TMCP summary generated with {len(summary['scans'])} scanners and {len(files)} files")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli())
