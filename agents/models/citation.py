"""
Unified Citation Model for RAG Responses.

This module defines a unified citation schema that works for both corpus sources
(Azure Cognitive Search) and web search sources (SERPR, Firecrawl, Cohere).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class CitationSource(str, Enum):
    """Source type for citations."""
    CORPUS = "corpus"
    WEB = "web"


class CitationProvider(str, Enum):
    """Provider type for citations."""
    AZURE_SEARCH = "azure_search"
    SERPR = "serpr"
    FIRECRAWL = "firecrawl"
    COHERE = "cohere"
    UNKNOWN = "unknown"


@dataclass
class Citation:
    """
    Unified citation model for RAG responses.
    
    This model works for both corpus sources (Azure Search) and web sources
    (SERPR, Firecrawl, Cohere). It includes conflict resolution logic.
    """
    # Required fields
    source: CitationSource
    provider: CitationProvider
    url: str
    title: str
    snippet: str
    
    # Optional metadata
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optional fields for different source types
    file_path: Optional[str] = None  # For corpus sources
    page_number: Optional[int] = None  # For corpus sources
    chunk_id: Optional[str] = None  # For corpus sources
    domain: Optional[str] = None  # For web sources
    timestamp: Optional[datetime] = None  # For web sources
    
    def canonical_url(self) -> str:
        """
        Get canonical URL for deduplication.
        Normalizes URLs to avoid duplicates.
        """
        url = self.url.lower().strip()
        # Remove common tracking parameters
        if "?" in url:
            base, params = url.split("?", 1)
            # Keep only essential parameters
            essential_params = []
            for param in params.split("&"):
                key = param.split("=")[0] if "=" in param else param
                # Keep essential params (customize as needed)
                if key not in ["utm_source", "utm_medium", "utm_campaign", "ref", "fbclid"]:
                    essential_params.append(param)
            if essential_params:
                url = f"{base}?{'&'.join(essential_params)}"
            else:
                url = base
        return url
    
    def dedup_key(self) -> str:
        """
        Generate a deduplication key for conflict resolution.
        Uses canonical URL + title hash.
        """
        import hashlib
        canonical = self.canonical_url()
        title_hash = hashlib.md5(self.title.encode()).hexdigest()[:8]
        return f"{canonical}:{title_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to dictionary for JSON serialization."""
        result = {
            "source": self.source.value,
            "provider": self.provider.value,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
        
        if self.file_path:
            result["file_path"] = self.file_path
        if self.page_number is not None:
            result["page_number"] = self.page_number
        if self.chunk_id:
            result["chunk_id"] = self.chunk_id
        if self.domain:
            result["domain"] = self.domain
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        """Create Citation from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            if isinstance(data["timestamp"], str):
                timestamp = datetime.fromisoformat(data["timestamp"])
            elif isinstance(data["timestamp"], datetime):
                timestamp = data["timestamp"]
        
        return cls(
            source=CitationSource(data.get("source", "corpus")),
            provider=CitationProvider(data.get("provider", "unknown")),
            url=data["url"],
            title=data["title"],
            snippet=data["snippet"],
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            file_path=data.get("file_path"),
            page_number=data.get("page_number"),
            chunk_id=data.get("chunk_id"),
            domain=data.get("domain"),
            timestamp=timestamp
        )
    
    @classmethod
    def from_azure_search(
        cls,
        doc: Dict[str, Any],
        snippet: str,
        confidence: float = 1.0
    ) -> "Citation":
        """Create Citation from Azure Cognitive Search document."""
        return cls(
            source=CitationSource.CORPUS,
            provider=CitationProvider.AZURE_SEARCH,
            url=doc.get("sourcepage", doc.get("sourcefile", "")),
            title=doc.get("title", doc.get("sourcefile", "Document")),
            snippet=snippet,
            confidence=confidence,
            metadata=doc,
            file_path=doc.get("sourcefile"),
            page_number=doc.get("page", doc.get("pagenum")),
            chunk_id=doc.get("id")
        )
    
    @classmethod
    def from_web_result(
        cls,
        result: Dict[str, Any],
        provider: CitationProvider,
        confidence: float = 1.0
    ) -> "Citation":
        """Create Citation from web search result."""
        from urllib.parse import urlparse
        
        url = result.get("url", result.get("link", ""))
        parsed = urlparse(url)
        
        return cls(
            source=CitationSource.WEB,
            provider=provider,
            url=url,
            title=result.get("title", result.get("name", "")),
            snippet=result.get("snippet", result.get("description", "")),
            confidence=confidence,
            metadata=result,
            domain=parsed.netloc,
            timestamp=datetime.now()  # Web results are current
        )


def resolve_citation_conflicts(
    citations: List[Citation],
    prefer_corpus: bool = True
) -> List[Citation]:
    """
    Resolve conflicts when the same source appears via corpus and web.
    
    Args:
        citations: List of citations (may include duplicates)
        prefer_corpus: If True, prefer corpus source over web when conflicting
        
    Returns:
        Deduplicated list of citations with conflicts resolved
    """
    # Group by dedup key
    citation_map: Dict[str, List[Citation]] = {}
    
    for citation in citations:
        key = citation.dedup_key()
        if key not in citation_map:
            citation_map[key] = []
        citation_map[key].append(citation)
    
    # Resolve conflicts
    resolved: List[Citation] = []
    
    for key, group in citation_map.items():
        if len(group) == 1:
            # No conflict
            resolved.append(group[0])
        else:
            # Conflict: same source via multiple providers
            corpus_citations = [c for c in group if c.source == CitationSource.CORPUS]
            web_citations = [c for c in group if c.source == CitationSource.WEB]
            
            if prefer_corpus and corpus_citations:
                # Prefer corpus source
                # Choose the one with highest confidence
                best = max(corpus_citations, key=lambda c: c.confidence)
                resolved.append(best)
            elif web_citations:
                # Use web source, prefer highest confidence
                best = max(web_citations, key=lambda c: c.confidence)
                resolved.append(best)
            else:
                # Fallback: use highest confidence
                best = max(group, key=lambda c: c.confidence)
                resolved.append(best)
    
    # Sort by confidence (highest first)
    resolved.sort(key=lambda c: c.confidence, reverse=True)
    
    return resolved





