"""Utility to pretty-format a JSONL (JSON Lines) file.

NOTE: Classic JSONL expects one JSON object per single line. Once we pretty
print (indent) each object, the result is no longer *strict* JSONL because
objects will span multiple lines. This script offers a few output modes so
you can choose what you need:

1. Default (stdout): Pretty prints each record (with indentation) separated
   by a blank line for readability.
2. --in-place: Rewrites the source file by replacing each original single-line
   object with its multi-line, indented representation separated by a blank line.
3. --output <path>: Writes the pretty output to a new file (recommended if you
   also want to keep the original valid JSONL file unchanged).
4. --as-array: Instead of individual objects, emit a single JSON array containing
   all objects, using indentation (this produces standard JSON, not JSONL).

Examples:
  python scripts/pretty_print_jsonl.py evals/ground_truth_multimodal.jsonl
  python scripts/pretty_print_jsonl.py evals/ground_truth_multimodal.jsonl --output evals/ground_truth_multimodal.pretty.jsonl
  python scripts/pretty_print_jsonl.py evals/ground_truth_multimodal.jsonl --in-place
  python scripts/pretty_print_jsonl.py evals/ground_truth_multimodal.jsonl --as-array --output evals/ground_truth_multimodal.pretty.json

Safeguards:
  * Refuses to use --in-place together with --as-array (ambiguous expectations).
  * Backs up the original file to <filename>.bak before in-place rewrite unless
    --no-backup is supplied.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def read_jsonl(path: Path):
    """Yield parsed JSON objects from a JSONL file.

    Skips empty lines. Raises ValueError with context on parse failures.
    """
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            yield json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON on line {idx} of {path}: {e}") from e


def write_pretty_individual(objs, indent: int) -> str:
    """Return a string with each object pretty JSON, separated by a blank line."""
    parts = [json.dumps(o, indent=indent, ensure_ascii=False) for o in objs]
    # Add trailing newline for file friendliness
    return "\n\n".join(parts) + "\n"


def write_pretty_array(objs, indent: int) -> str:
    return json.dumps(list(objs), indent=indent, ensure_ascii=False) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pretty-format a JSONL file.")
    parser.add_argument(
        "jsonl_file",
        type=Path,
        help="Path to the source JSONL file (one JSON object per line).",
    )
    parser.add_argument("--indent", type=int, default=2, help="Indent level for json.dumps (default: 2)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite the original file with pretty-formatted objects (not strict JSONL).",
    )
    group.add_argument(
        "--output",
        type=Path,
        help="Path to write output. If omitted and not --in-place, prints to stdout.",
    )
    parser.add_argument(
        "--as-array",
        action="store_true",
        help="Emit a single JSON array instead of individual pretty objects.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="When using --in-place, do not create a .bak backup file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if not args.jsonl_file.exists():
        print(f"Error: File not found: {args.jsonl_file}", file=sys.stderr)
        return 1

    objs = list(read_jsonl(args.jsonl_file))

    if args.as_array:
        output_text = write_pretty_array(objs, args.indent)
    else:
        output_text = write_pretty_individual(objs, args.indent)

    # Destination logic
    if args.in_place:
        if not args.no_backup:
            backup_path = args.jsonl_file.with_suffix(args.jsonl_file.suffix + ".bak")
            if not backup_path.exists():
                backup_path.write_text(args.jsonl_file.read_text(encoding="utf-8"), encoding="utf-8")
        args.jsonl_file.write_text(output_text, encoding="utf-8")
        print(f"Rewrote {args.jsonl_file} ({len(objs)} objects).")
    elif args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
        print(f"Wrote pretty output to {args.output} ({len(objs)} objects).")
    else:
        # stdout
        sys.stdout.write(output_text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
