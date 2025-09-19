"""
RAG Service for Microsoft 365 Agent.
This service integrates the existing RAG functionality with the agent framework.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.identity.aio import DefaultAzureCredential

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
    RAG Service that integrates existing RAG functionality with the agent framework.
    This service acts as a bridge between the Microsoft 365 Agent and the existing RAG system.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._openai_client: Optional[AsyncOpenAI] = None
        self._search_client: Optional[SearchClient] = None
        self._search_index_client: Optional[SearchIndexClient] = None
    
    async def initialize(self) -> None:
        """Initialize the RAG service with Azure clients."""
        try:
            # Initialize OpenAI client
            self._openai_client = AsyncOpenAI(
                api_key=self.config.azure_openai_api_key,
                azure_endpoint=self.config.azure_openai_endpoint,
                api_version="2024-10-21"
            )
            
            # Initialize Azure Search clients
            credential = DefaultAzureCredential()
            self._search_client = SearchClient(
                endpoint=self.config.azure_search_endpoint,
                index_name=self.config.azure_search_index,
                credential=credential
            )
            
            self._search_index_client = SearchIndexClient(
                endpoint=self.config.azure_search_endpoint,
                credential=credential
            )
            
            logger.info("RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            raise
    
    async def process_query(self, request: RAGRequest) -> RAGResponse:
        """
        Process a RAG query and return a response.
        This method integrates with the existing RAG approaches.
        """
        try:
            if not self._openai_client or not self._search_client:
                await self.initialize()
            
            # Convert conversation history to the format expected by existing approaches
            messages = self._format_messages(request.message, request.conversation_history)
            
            # Create context for the RAG processing
            context = {
                "auth_claims": {"oid": request.user_id},
                "channel_id": request.channel_id,
                **(request.context or {})
            }
            
            # For now, we'll use a simplified RAG approach
            # In the next phase, we'll integrate with the existing Approach classes
            response = await self._simple_rag_query(messages, context)
            
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
        Process a RAG query with streaming response.
        """
        try:
            if not self._openai_client or not self._search_client:
                await self.initialize()
            
            # Convert conversation history to the format expected by existing approaches
            messages = self._format_messages(request.message, request.conversation_history)
            
            # Create context for the RAG processing
            context = {
                "auth_claims": {"oid": request.user_id},
                "channel_id": request.channel_id,
                **(request.context or {})
            }
            
            # Stream the response
            async for chunk in self._simple_rag_query_stream(messages, context):
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
    
    async def _simple_rag_query(self, messages: List[Dict[str, str]], context: Dict[str, Any]) -> RAGResponse:
        """
        Simplified RAG query implementation.
        This will be replaced with integration to existing Approach classes in the next phase.
        """
        try:
            # For now, we'll use a simple OpenAI completion
            # This will be replaced with the full RAG implementation
            response = await self._openai_client.chat.completions.create(
                model=self.config.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that can answer questions about documents. Provide accurate, helpful responses based on the available information."},
                    *messages
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content or "I couldn't generate a response."
            
            return RAGResponse(
                answer=answer,
                sources=[],
                citations=[],
                thoughts=[{"title": "Response Generated", "description": "Generated response using OpenAI"}],
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                model_info={
                    "model": self.config.azure_openai_deployment,
                    "temperature": "0.3"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in simple RAG query: {e}")
            raise
    
    async def _simple_rag_query_stream(self, messages: List[Dict[str, str]], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simplified streaming RAG query implementation.
        """
        try:
            stream = await self._openai_client.chat.completions.create(
                model=self.config.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that can answer questions about documents. Provide accurate, helpful responses based on the available information."},
                    *messages
                ],
                max_tokens=1000,
                temperature=0.3,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "type": "content",
                        "content": chunk.choices[0].delta.content
                    }
            
        except Exception as e:
            logger.error(f"Error in streaming RAG query: {e}")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}"
            }
    
    async def close(self) -> None:
        """Close the RAG service and clean up resources."""
        if self._openai_client:
            await self._openai_client.close()
        if self._search_client:
            await self._search_client.close()
        if self._search_index_client:
            await self._search_index_client.close()