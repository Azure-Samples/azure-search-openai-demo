"""
Copilot-specific handler for Microsoft 365 Copilot integration.
This handler processes Copilot plugin requests and formats responses for Copilot.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from botbuilder.core import TurnContext
from botbuilder.schema import Activity, ActivityTypes

from services.rag_service import RAGService, RAGRequest, RAGResponse
from services.auth_service import AuthService
from models.citation import Citation, CitationSource, resolve_citation_conflicts


logger = logging.getLogger(__name__)


@dataclass
class CopilotRequest:
    """Request from Copilot plugin."""
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    max_results: Optional[int] = 5
    context: Optional[Dict[str, Any]] = None


@dataclass
class CopilotResponse:
    """Response formatted for Copilot."""
    answer: str
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class CopilotHandler:
    """
    Handler for Microsoft Copilot plugin requests.
    Formats responses specifically for Copilot consumption.
    """
    
    def __init__(self, rag_service: RAGService, auth_service: AuthService):
        self.rag_service = rag_service
        self.auth_service = auth_service
        logger.info("CopilotHandler initialized")
    
    async def handle_search_request(
        self,
        request: CopilotRequest,
        auth_claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a search request from Copilot.
        Returns document search results.
        """
        try:
            # Create RAG request for search
            rag_request = RAGRequest(
                message=request.query,
                conversation_history=request.conversation_history or [],
                user_id=auth_claims.get("oid", ""),
                channel_id="copilot",
                context={
                    "auth_claims": auth_claims,
                    "copilot_request": True,
                    "max_results": request.max_results
                }
            )
            
            # Process with RAG service (this will search backend)
            rag_response = await self.rag_service.process_query(rag_request)
            
            # Format for Copilot
            results = []
            
            # Convert sources to Copilot format
            for source in rag_response.sources[:request.max_results or 5]:
                if isinstance(source, dict):
                    results.append({
                        "title": source.get("title", source.get("sourcefile", "Document")),
                        "url": source.get("url", source.get("sourcepage", "")),
                        "snippet": source.get("content", source.get("snippet", "")),
                        "source": "corpus"
                    })
            
            # Add citations if available
            if rag_response.unified_citations:
                for citation in rag_response.unified_citations[:request.max_results or 5]:
                    if citation.source == CitationSource.CORPUS:
                        results.append({
                            "title": citation.title,
                            "url": citation.url,
                            "snippet": citation.snippet,
                            "source": "corpus"
                        })
            
            return {
                "results": results,
                "totalCount": len(results),
                "query": request.query
            }
            
        except Exception as e:
            logger.error(f"Error handling Copilot search request: {e}", exc_info=True)
            return {
                "results": [],
                "totalCount": 0,
                "error": str(e)
            }
    
    async def handle_query_request(
        self,
        request: CopilotRequest,
        auth_claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a query request from Copilot.
        Returns AI-generated answer with citations.
        """
        try:
            # Create RAG request
            rag_request = RAGRequest(
                message=request.query,
                conversation_history=request.conversation_history or [],
                user_id=auth_claims.get("oid", ""),
                channel_id="copilot",
                context={
                    "auth_claims": auth_claims,
                    "copilot_request": True
                }
            )
            
            # Process with RAG service
            rag_response = await self.rag_service.process_query(rag_request)
            
            # Format citations for Copilot
            citations = []
            
            # Use unified citations if available
            if rag_response.unified_citations:
                resolved_citations = resolve_citation_conflicts(
                    rag_response.unified_citations,
                    prefer_corpus=True
                )
                
                for citation in resolved_citations:
                    citations.append({
                        "title": citation.title,
                        "url": citation.url,
                        "snippet": citation.snippet[:200] if citation.snippet else "",
                        "source": citation.source.value,
                        "provider": citation.provider.value
                    })
            else:
                # Fallback to legacy citations
                for citation_str in rag_response.citations:
                    if citation_str:
                        citations.append({
                            "title": citation_str[:100],
                            "url": "",
                            "snippet": citation_str,
                            "source": "unknown"
                        })
            
            # Format response for Copilot
            response = {
                "answer": rag_response.answer,
                "citations": citations
            }
            
            # Add thoughts if available and requested
            if rag_response.thoughts:
                response["thoughts"] = [
                    {
                        "title": thought.get("title", ""),
                        "description": thought.get("description", "")
                    }
                    for thought in rag_response.thoughts
                ]
            
            # Add metadata
            if rag_response.token_usage:
                response["metadata"] = {
                    "token_usage": rag_response.token_usage,
                    "model_info": rag_response.model_info
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling Copilot query request: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error processing your request: {str(e)}",
                "citations": [],
                "error": str(e)
            }
    
    async def handle_activity(
        self,
        turn_context: TurnContext,
        auth_claims: Dict[str, Any]
    ) -> Optional[Activity]:
        """
        Handle incoming Copilot activity.
        Routes to appropriate handler based on activity type.
        """
        try:
            # Extract request from activity
            activity = turn_context.activity
            
            if activity.type != ActivityTypes.message:
                return None
            
            # Check if this is a Copilot request
            channel_data = activity.channel_data or {}
            if channel_data.get("channelId") != "copilot":
                return None
            
            # Parse request from activity value or text
            request_data = {}
            if activity.value:
                request_data = activity.value
            elif activity.text:
                # Simple text query
                request_data = {
                    "query": activity.text,
                    "type": "query"
                }
            else:
                return None
            
            request_type = request_data.get("type", "query")
            
            # Create Copilot request
            copilot_request = CopilotRequest(
                query=request_data.get("query", request_data.get("message", "")),
                conversation_history=request_data.get("conversationHistory", []),
                max_results=request_data.get("maxResults", 5),
                context=request_data.get("context", {})
            )
            
            # Route to appropriate handler
            if request_type == "search":
                result = await self.handle_search_request(copilot_request, auth_claims)
            else:
                # Default to query
                result = await self.handle_query_request(copilot_request, auth_claims)
            
            # Return formatted response
            response_activity = Activity(
                type=ActivityTypes.message,
                channel_id="copilot",
                text=str(result.get("answer", result))
            )
            response_activity.value = result
            
            return response_activity
            
        except Exception as e:
            logger.error(f"Error handling Copilot activity: {e}", exc_info=True)
            return None





