"""
Response Adapter for Microsoft 365 Agent.
This adapter formats RAG responses for different Microsoft 365 channels.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from services.rag_service import RAGResponse


logger = logging.getLogger(__name__)


@dataclass
class FormattedResponse:
    """Formatted response for a specific channel."""
    text: str
    attachments: Optional[List[Dict[str, Any]]] = None
    suggested_actions: Optional[List[Dict[str, Any]]] = None
    channel_specific: Optional[Dict[str, Any]] = None


class ResponseAdapter:
    """
    Adapter that formats RAG responses for different Microsoft 365 channels.
    This ensures consistent user experience across Teams, Copilot, and other channels.
    """
    
    def __init__(self):
        self.max_response_length = 4000  # Maximum length for most channels
        self.max_sources = 5  # Maximum number of sources to show
        self.max_citations = 3  # Maximum number of citations to show
    
    async def format_response(
        self,
        rag_response: RAGResponse,
        channel_id: str
    ) -> Dict[str, Any]:
        """
        Format a RAG response for the specified channel.
        """
        try:
            if channel_id == "msteams":
                return await self._format_for_teams(rag_response)
            elif channel_id == "webchat":
                return await self._format_for_web_chat(rag_response)
            elif channel_id == "email":
                return await self._format_for_email(rag_response)
            else:
                return await self._format_for_default(rag_response)
                
        except Exception as e:
            logger.error(f"Error formatting response for channel {channel_id}: {e}")
            return await self._format_for_default(rag_response)
    
    async def _format_for_teams(self, rag_response: RAGResponse) -> Dict[str, Any]:
        """
        Format response specifically for Microsoft Teams.
        Teams supports rich formatting, adaptive cards, and interactive elements.
        """
        try:
            # Base response text
            response_text = rag_response.answer
            
            # Add sources if available
            if rag_response.sources:
                sources_text = "\n\n**📚 Sources:**\n"
                for i, source in enumerate(rag_response.sources[:self.max_sources], 1):
                    source_title = source.get("title", "Unknown Source")
                    source_url = source.get("url", "")
                    if source_url:
                        sources_text += f"{i}. [{source_title}]({source_url})\n"
                    else:
                        sources_text += f"{i}. {source_title}\n"
                response_text += sources_text
            
            # Add citations if available
            if rag_response.citations:
                citations_text = "\n\n**🔗 Citations:**\n"
                for i, citation in enumerate(rag_response.citations[:self.max_citations], 1):
                    citations_text += f"{i}. {citation}\n"
                response_text += citations_text
            
            # Add thoughts if available (for debugging/transparency)
            if rag_response.thoughts:
                thoughts_text = "\n\n**💭 Process:**\n"
                for thought in rag_response.thoughts[:2]:  # Limit to 2 thoughts
                    thoughts_text += f"• {thought.get('title', 'Step')}: {thought.get('description', '')}\n"
                response_text += thoughts_text
            
            # Create suggested actions for Teams
            suggested_actions = [
                {
                    "type": "imBack",
                    "title": "Ask Follow-up",
                    "value": "Can you provide more details about this?"
                },
                {
                    "type": "imBack",
                    "title": "Search Related",
                    "value": "Find more information about this topic"
                },
                {
                    "type": "imBack",
                    "title": "Summarize",
                    "value": "Can you summarize the key points?"
                }
            ]
            
            return {
                "text": response_text,
                "suggested_actions": suggested_actions,
                "channel_specific": {
                    "teams": {
                        "supports_adaptive_cards": True,
                        "supports_mentions": True,
                        "supports_file_uploads": True
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting for Teams: {e}")
            return await self._format_for_default(rag_response)
    
    async def _format_for_web_chat(self, rag_response: RAGResponse) -> Dict[str, Any]:
        """
        Format response for web chat interface.
        Web chat supports rich HTML formatting and interactive elements.
        """
        try:
            # Base response text with HTML formatting
            response_text = rag_response.answer
            
            # Add sources with HTML links
            if rag_response.sources:
                sources_html = "\n\n<strong>📚 Sources:</strong><br>"
                for i, source in enumerate(rag_response.sources[:self.max_sources], 1):
                    source_title = source.get("title", "Unknown Source")
                    source_url = source.get("url", "")
                    if source_url:
                        sources_html += f"{i}. <a href='{source_url}' target='_blank'>{source_title}</a><br>"
                    else:
                        sources_html += f"{i}. {source_title}<br>"
                response_text += sources_html
            
            # Add citations
            if rag_response.citations:
                citations_html = "\n\n<strong>🔗 Citations:</strong><br>"
                for i, citation in enumerate(rag_response.citations[:self.max_citations], 1):
                    citations_html += f"{i}. {citation}<br>"
                response_text += citations_html
            
            # Create quick reply buttons
            suggested_actions = [
                {
                    "type": "postBack",
                    "title": "Ask Follow-up",
                    "value": "Can you provide more details about this?"
                },
                {
                    "type": "postBack",
                    "title": "Search Related",
                    "value": "Find more information about this topic"
                },
                {
                    "type": "postBack",
                    "title": "New Question",
                    "value": "I have a different question"
                }
            ]
            
            return {
                "text": response_text,
                "suggested_actions": suggested_actions,
                "channel_specific": {
                    "web_chat": {
                        "supports_html": True,
                        "supports_quick_replies": True,
                        "supports_typing_indicator": True
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting for web chat: {e}")
            return await self._format_for_default(rag_response)
    
    async def _format_for_email(self, rag_response: RAGResponse) -> Dict[str, Any]:
        """
        Format response for email channels.
        Email has limited formatting options and should be concise.
        """
        try:
            # Base response text (plain text)
            response_text = rag_response.answer
            
            # Add sources (plain text)
            if rag_response.sources:
                sources_text = "\n\nSources:\n"
                for i, source in enumerate(rag_response.sources[:self.max_sources], 1):
                    source_title = source.get("title", "Unknown Source")
                    source_url = source.get("url", "")
                    if source_url:
                        sources_text += f"{i}. {source_title} - {source_url}\n"
                    else:
                        sources_text += f"{i}. {source_title}\n"
                response_text += sources_text
            
            # Add citations (plain text)
            if rag_response.citations:
                citations_text = "\n\nCitations:\n"
                for i, citation in enumerate(rag_response.citations[:self.max_citations], 1):
                    citations_text += f"{i}. {citation}\n"
                response_text += citations_text
            
            # Truncate if too long for email
            if len(response_text) > 2000:
                response_text = response_text[:2000] + "\n\n[Response truncated for email]"
            
            return {
                "text": response_text,
                "channel_specific": {
                    "email": {
                        "supports_html": False,
                        "max_length": 2000,
                        "plain_text_only": True
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting for email: {e}")
            return await self._format_for_default(rag_response)
    
    async def _format_for_default(self, rag_response: RAGResponse) -> Dict[str, Any]:
        """
        Format response for default/unknown channels.
        This provides a basic, universally compatible format.
        """
        try:
            # Base response text
            response_text = rag_response.answer
            
            # Add sources (simple format)
            if rag_response.sources:
                sources_text = "\n\nSources:\n"
                for i, source in enumerate(rag_response.sources[:self.max_sources], 1):
                    source_title = source.get("title", "Unknown Source")
                    sources_text += f"{i}. {source_title}\n"
                response_text += sources_text
            
            # Add citations (simple format)
            if rag_response.citations:
                citations_text = "\n\nCitations:\n"
                for i, citation in enumerate(rag_response.citations[:self.max_citations], 1):
                    citations_text += f"{i}. {citation}\n"
                response_text += citations_text
            
            return {
                "text": response_text,
                "channel_specific": {
                    "default": {
                        "supports_html": False,
                        "supports_attachments": False,
                        "plain_text_only": True
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting for default: {e}")
            return {
                "text": rag_response.answer or "I'm sorry, I couldn't generate a response.",
                "channel_specific": {}
            }
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length while preserving word boundaries."""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can find a good break point
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    def _format_source_url(self, source: Dict[str, Any]) -> str:
        """Format a source URL for display."""
        url = source.get("url", "")
        title = source.get("title", "Unknown Source")
        
        if url:
            return f"[{title}]({url})"
        else:
            return title