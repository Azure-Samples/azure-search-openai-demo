#!/usr/bin/env python3
"""CLI entry point for TMCP scan aggregation."""

from __future__ import annotations

import sys

from tmcp.aggregate import cli

if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli())
