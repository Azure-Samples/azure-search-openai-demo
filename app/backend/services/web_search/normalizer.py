from typing import List, Dict, Any


def normalize_serper(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in items or []:
        normalized.append(
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", item.get("description", "")),
                "provider": "serper",
            }
        )
    return normalized


