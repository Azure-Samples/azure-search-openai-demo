import json
from pathlib import Path


def load_config(config_path: Path) -> dict:
    """Load a JSON configuration file."""
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]


def save_jsonl(data: list[dict], path: Path):
    """Save a list of dictionaries to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
