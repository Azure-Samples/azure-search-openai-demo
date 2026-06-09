import json
from pathlib import Path

import pytest

LOCALES_DIR = Path(__file__).parent.parent / "app" / "frontend" / "src" / "locales"
REFERENCE_LOCALE = "en"


def flatten_keys(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= flatten_keys(value, full_key)
        else:
            keys.add(full_key)
    return keys


def load_locale(locale: str) -> dict:
    return json.loads((LOCALES_DIR / locale / "translation.json").read_text(encoding="utf-8"))


def all_locales() -> list[str]:
    return sorted(path.name for path in LOCALES_DIR.iterdir() if path.is_dir())


def test_reference_locale_exists():
    assert (LOCALES_DIR / REFERENCE_LOCALE / "translation.json").exists()


@pytest.mark.parametrize("locale", [loc for loc in all_locales() if loc != REFERENCE_LOCALE])
def test_locale_keys_match_reference(locale: str):
    reference_keys = flatten_keys(load_locale(REFERENCE_LOCALE))
    locale_keys = flatten_keys(load_locale(locale))
    missing = reference_keys - locale_keys
    extra = locale_keys - reference_keys
    assert not missing, f"{locale} is missing keys present in {REFERENCE_LOCALE}: {sorted(missing)}"
    assert not extra, f"{locale} has keys not present in {REFERENCE_LOCALE}: {sorted(extra)}"
