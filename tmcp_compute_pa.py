#!/usr/bin/env python3
"""CLI entry for computing TMCP P/A."""

from __future__ import annotations

import sys

from tmcp.pa import cli

if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli())
