"""
Shared utility functions for the ingestion module.
"""

import logging
from typing import Optional

logger = logging.getLogger("ingestion")


def clean_key_if_exists(key: Optional[str]) -> Optional[str]:
    """Remove leading and trailing whitespace from a key if it exists.

    Args:
        key: The key string to clean

    Returns:
        Cleaned key or None if key is empty/None
    """
    if key is not None and key.strip() != "":
        return key.strip()
    return None
