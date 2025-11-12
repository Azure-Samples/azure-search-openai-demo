"""
RAG Service for Microsoft 365 Agent.
This service calls the existing backend API instead of duplicating RAG logic.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, TYPE_CHECKING
from dataclasses import dataclass, field
import aiohttp
import json

from config.agent_config import AgentConfig

if TYPE_CHECKING:
    from models.citation import Citation


logger = logging.getLogger(__name__)


@dataclass
class RAGRequest:
    """Request for RAG processing."""
    message: str
    conversation_history: List[Dict[str, str]]
    user_id: str
    channel_id: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class RAGResponse:
    """Response from RAG processing."""
    answer: str
    sources: List[Dict[str, Any]]
    citations: List[str]  # Legacy format - string citations
    thoughts: List[Dict[str, Any]]
    token_usage: Optional[Dict[str, int]] = None
    model_info: Optional[Dict[str, str]] = None
    unified_citations: Optional[List['Citation']] = None  # New unified citation format


class RAGService:
    """
    RAG Service that calls the existing backend API.
    This service acts as a bridge between the Microsoft 365 Agent and the existing backend.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._backend_url = config.backend_url
    
    async def initialize(self) -> None:
        """Initialize the RAG service with HTTP client."""
        try:
            # Initialize HTTP session for calling backend
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Microsoft365Agent/1.0"
                }
            )
            
            logger.info("RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            raise
    
    async def process_query(self, request: RAGRequest) -> RAGResponse:
        """
        Process a RAG query by calling the existing backend API.
        """
        try:
            if not self._http_session:
                await self.initialize()
            
            # Convert conversation history to the format expected by backend
            messages = self._format_messages(request.message, request.conversation_history)
            
            # Create context for the RAG processing
            context = {
                "auth_claims": {"oid": request.user_id},
                "channel_id": request.channel_id,
                **(request.context or {})
            }
            
            # Call the existing backend /chat endpoint
            response = await self._call_backend_chat(messages, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing RAG query: {e}")
            return RAGResponse(
                answer="I'm sorry, I encountered an error processing your request. Please try again.",
                sources=[],
                citations=[],
                thoughts=[{"title": "Error", "description": str(e)}]
            )
    
    async def process_query_stream(self, request: RAGRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a RAG query with streaming response by calling backend.
        """
        try:
            if not self._http_session:
                await self.initialize()
            
            # Convert conversation history to the format expected by backend
            messages = self._format_messages(request.message, request.conversation_history)
            
            # Create context for the RAG processing
            context = {
                "auth_claims": {"oid": request.user_id},
                "channel_id": request.channel_id,
                **(request.context or {})
            }
            
            # Stream the response from backend
            async for chunk in self._call_backend_chat_stream(messages, context):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error processing streaming RAG query: {e}")
            yield {
                "type": "error",
                "content": "I'm sorry, I encountered an error processing your request. Please try again.",
                "error": str(e)
            }
    
    def _format_messages(self, message: str, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for the RAG system."""
        messages = []
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    async def _call_backend_chat(self, messages: List[Dict[str, str]], context: Dict[str, Any]) -> RAGResponse:
        """
        Call the existing backend /chat endpoint.
        """
        try:
            # Prepare the request payload
            payload = {
                "messages": messages,
                "context": context,
                "session_state": None  # Will be managed by the agent
            }
            
            # For webchat/local testing, we may not have auth tokens
            # The backend will handle this via get_auth_claims_if_enabled
            headers = {}
            if "auth_claims" in context and context["auth_claims"].get("access_token"):
                headers["Authorization"] = f"Bearer {context['auth_claims']['access_token']}"
            # Propagate correlation id if present
            if context.get("traceparent"):
                headers["x-traceparent"] = str(context["traceparent"])  # simple correlation header
            
            # Make the request to the backend
            async with self._http_session.post(
                f"{self._backend_url}/chat",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Force print for debugging (always visible)
                    print(f"\n{'='*60}")
                    print(f"[RAG SERVICE] Backend response received")
                    print(f"[RAG SERVICE] Response keys: {list(data.keys())}")
                    if "message" in data:
                        print(f"[RAG SERVICE] Message type: {type(data['message'])}")
                        if isinstance(data.get('message'), dict):
                            print(f"[RAG SERVICE] Message keys: {list(data['message'].keys())}")
                            print(f"[RAG SERVICE] Message content preview: {str(data['message'].get('content', ''))[:100]}")
                    
                    # Backend returns: { "message": { "content": "...", "role": "..." }, "context": { "data_points": {...}, "thoughts": [...] } }
                    # Extract answer from message.content
                    answer = ""
                    if "message" in data and isinstance(data["message"], dict):
                        answer = data["message"].get("content", "")
                        print(f"[RAG SERVICE] ✓ Extracted answer from message.content (length: {len(answer)})")
                        logger.info(f"Extracted answer from message.content: {answer[:100]}...")
                    elif "answer" in data:
                        # Fallback for different response format
                        answer = data.get("answer", "")
                        print(f"[RAG SERVICE] ✓ Extracted answer from answer field (length: {len(answer)})")
                        logger.info(f"Extracted answer from answer field: {answer[:100]}...")
                    else:
                        print(f"[RAG SERVICE] ✗ Could not find answer! Available keys: {list(data.keys())}")
                        logger.warning(f"Could not find answer in response. Available keys: {list(data.keys())}")
                        # Try to find any content field
                        if "content" in data:
                            answer = data.get("content", "")
                            print(f"[RAG SERVICE] ✓ Found answer in content field (length: {len(answer)})")
                    print(f"{'='*60}\n")
                    
                    # Extract data points from context
                    context = data.get("context", {})
                    data_points = context.get("data_points", {})
                    text_sources = data_points.get("text", [])
                    citations = data_points.get("citations", [])
                    thoughts = context.get("thoughts", [])
                    
                    # Convert backend citations to unified format
                    unified_citations = self._convert_to_unified_citations(
                        text_sources,
                        citations
                    )
                    
                    # Convert backend response to RAGResponse
                    return RAGResponse(
                        answer=answer,
                        sources=text_sources,
                        citations=citations,
                        thoughts=thoughts,
                        token_usage=data.get("token_usage"),
                        model_info=data.get("model_info"),
                        unified_citations=unified_citations
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Backend API error {response.status}: {error_text}")
                    raise Exception(f"Backend API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error calling backend chat API: {e}")
            raise
    
    def _convert_to_unified_citations(
        self,
        sources: List[Dict[str, Any]],
        citations: List[str]
    ) -> List['Citation']:
        """
        Convert backend citations to unified Citation format.
        
        Args:
            sources: List of source documents from backend
            citations: List of citation strings from backend
            
        Returns:
            List of unified Citation objects
        """
        try:
            from models.citation import Citation, CitationSource, CitationProvider
            
            unified: List[Citation] = []
            
            # Convert sources (corpus sources)
            for source in sources:
                if isinstance(source, dict):
                    try:
                        citation = Citation.from_azure_search(
                            doc=source,
                            snippet=source.get("content", ""),
                            confidence=1.0
                        )
                        unified.append(citation)
                    except Exception as e:
                        logger.warning(f"Error converting source to citation: {e}")
            
            # Convert citation strings (if any)
            for citation_str in citations:
                if citation_str:
                    # Try to parse citation string
                    # Format may vary, attempt to extract URL
                    import re
                    url_match = re.search(r'https?://[^\s<>"\']+', citation_str)
                    if url_match:
                        try:
                            citation = Citation(
                                source=CitationSource.WEB,
                                provider=CitationProvider.UNKNOWN,
                                url=url_match.group(0),
                                title=citation_str[:100],  # Use citation string as title
                                snippet=citation_str,
                                confidence=0.8  # Lower confidence for string citations
                            )
                            unified.append(citation)
                        except Exception as e:
                            logger.warning(f"Error converting citation string: {e}")
            
            return unified
            
        except ImportError:
            logger.warning("Citation model not available, skipping unified citation conversion")
            return []
        except Exception as e:
            logger.error(f"Error converting to unified citations: {e}", exc_info=True)
            return []
    
    async def _call_backend_chat_stream(self, messages: List[Dict[str, str]], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Call the existing backend /chat/stream endpoint.
        """
        try:
            # Prepare the request payload
            payload = {
                "messages": messages,
                "context": context,
                "session_state": None  # Will be managed by the agent
            }
            
            # Make the streaming request to the backend
            async with self._http_session.post(
                f"{self._backend_url}/chat/stream",
                json=payload
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            try:
                                # Parse NDJSON line
                                chunk_data = json.loads(line.decode('utf-8'))
                                yield chunk_data
                            except json.JSONDecodeError:
                                # Skip invalid JSON lines
                                continue
                else:
                    error_text = await response.text()
                    logger.error(f"Backend streaming API error {response.status}: {error_text}")
                    yield {
                        "type": "error",
                        "content": f"Backend API error: {response.status}"
                    }
                    
        except Exception as e:
            logger.error(f"Error calling backend streaming API: {e}")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}"
            }
    
    async def close(self) -> None:
        """Close the RAG service and clean up resources."""
        if self._http_session:
            await self._http_session.close()