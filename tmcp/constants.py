"""Shared constants for TMCP tooling."""

from __future__ import annotations

from typing import Dict, List

from . import TMCP_VERSION

SEVERITY_LEVELS: List[str] = ["critical", "high", "medium", "low", "info"]
DEFAULT_SEVERITY_WEIGHTS: Dict[str, float] = {
    "critical": 15.0,
    "high": 8.0,
    "medium": 3.0,
    "low": 1.0,
    "info": 0.0,
}
# Findings at or above this level are treated as blockers automatically
BLOCKER_SEVERITIES = {"critical"}
CAP_VALUE = 20.0
KAPPA = 1.0
TMCP_SUMMARY_VERSION = TMCP_VERSION
