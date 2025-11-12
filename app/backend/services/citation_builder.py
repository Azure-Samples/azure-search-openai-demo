from typing import List, Dict, Any


def build_unified_from_text_sources(text_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unified: List[Dict[str, Any]] = []
    for doc in text_sources or []:
        unified.append(
            {
                "source": "corpus",
                "provider": "azure_search",
                "url": doc.get("sourcepage", doc.get("sourcefile", "")),
                "title": doc.get("title", doc.get("sourcefile", "Document")),
                "snippet": doc.get("content", ""),
                "metadata": doc,
            }
        )
    return unified


