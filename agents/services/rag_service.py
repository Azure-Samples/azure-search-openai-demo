"""
RAG Service for Microsoft 365 Agent.
This service calls the existing backend API instead of duplicating RAG logic.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import aiohttp
import json

from config.agent_config import AgentConfig


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
    citations: List[str]
    thoughts: List[Dict[str, Any]]
    token_usage: Optional[Dict[str, int]] = None
    model_info: Optional[Dict[str, str]] = None


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
            
            # Make the request to the backend
            async with self._http_session.post(
                f"{self._backend_url}/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert backend response to RAGResponse
                    return RAGResponse(
                        answer=data.get("answer", ""),
                        sources=data.get("data_points", {}).get("text", []),
                        citations=data.get("data_points", {}).get("citations", []),
                        thoughts=data.get("thoughts", []),
                        token_usage=data.get("token_usage"),
                        model_info=data.get("model_info")
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Backend API error {response.status}: {error_text}")
                    raise Exception(f"Backend API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error calling backend chat API: {e}")
            raise
    
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