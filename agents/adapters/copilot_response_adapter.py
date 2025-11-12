"""
Copilot-specific response adapter for formatting responses for Microsoft Copilot.
This adapter formats RAG responses specifically for Copilot UI consumption.
"""

import logging
from typing import Dict, Any, List, Optional

from services.rag_service import RAGResponse
from models.citation import Citation, CitationSource, resolve_citation_conflicts


logger = logging.getLogger(__name__)


class CopilotResponseAdapter:
    """
    Response adapter for Microsoft Copilot plugin.
    Formats responses to be consumed by Copilot UI.
    """
    
    def __init__(self):
        logger.info("CopilotResponseAdapter initialized")
    
    def format_rag_response(
        self,
        rag_response: RAGResponse,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Format a RAG response for Copilot.
        
        Args:
            rag_response: RAG response from backend
            include_metadata: Whether to include token usage and model info
            
        Returns:
            Formatted response dictionary for Copilot
        """
        try:
            # Start with answer
            response = {
                "answer": rag_response.answer
            }
            
            # Format citations
            citations = self._format_citations(rag_response)
            if citations:
                response["citations"] = citations
            
            # Add sources (for Copilot's source tracking)
            sources = self._format_sources(rag_response)
            if sources:
                response["sources"] = sources
            
            # Add thoughts if available
            if rag_response.thoughts:
                response["thoughts"] = [
                    {
                        "title": thought.get("title", ""),
                        "description": thought.get("description", "")
                    }
                    for thought in rag_response.thoughts
                ]
            
            # Add metadata if requested
            if include_metadata:
                metadata = {}
                if rag_response.token_usage:
                    metadata["token_usage"] = rag_response.token_usage
                if rag_response.model_info:
                    metadata["model_info"] = rag_response.model_info
                if metadata:
                    response["metadata"] = metadata
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting Copilot response: {e}", exc_info=True)
            return {
                "answer": rag_response.answer,
                "citations": [],
                "error": str(e)
            }
    
    def _format_citations(
        self,
        rag_response: RAGResponse
    ) -> List[Dict[str, Any]]:
        """
        Format citations for Copilot.
        Uses unified citations if available, falls back to legacy format.
        """
        citations = []
        
        # Prefer unified citations
        if rag_response.unified_citations:
            # Resolve conflicts (prefer corpus)
            resolved = resolve_citation_conflicts(
                rag_response.unified_citations,
                prefer_corpus=True
            )
            
            for citation in resolved:
                citations.append({
                    "title": citation.title,
                    "url": citation.url,
                    "snippet": citation.snippet[:300] if citation.snippet else "",
                    "source": citation.source.value,
                    "provider": citation.provider.value,
                    "confidence": citation.confidence
                })
        else:
            # Fallback to legacy citations
            for citation_str in rag_response.citations:
                if citation_str:
                    citations.append({
                        "title": citation_str[:100],
                        "url": "",
                        "snippet": citation_str,
                        "source": "unknown",
                        "provider": "unknown"
                    })
        
        return citations
    
    def _format_sources(
        self,
        rag_response: RAGResponse
    ) -> List[Dict[str, Any]]:
        """
        Format sources for Copilot's source tracking.
        """
        sources = []
        
        # Add sources from rag_response.sources
        for source in rag_response.sources:
            if isinstance(source, dict):
                sources.append({
                    "title": source.get("title", source.get("sourcefile", "Document")),
                    "url": source.get("url", source.get("sourcepage", "")),
                    "type": "document"
                })
        
        return sources
    
    def format_search_results(
        self,
        results: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Format search results for Copilot search endpoint.
        """
        formatted_results = []
        
        for result in results:
            formatted_results.append({
                "title": result.get("title", "Document"),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", result.get("content", ""))[:300],
                "source": result.get("source", "corpus")
            })
        
        return {
            "results": formatted_results,
            "totalCount": len(formatted_results),
            "query": query
        }
    
    def format_error_response(
        self,
        error_message: str,
        error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format error response for Copilot.
        """
        response = {
            "answer": f"I encountered an error: {error_message}",
            "citations": [],
            "error": error_message
        }
        
        if error_code:
            response["error_code"] = error_code
        
        return response





