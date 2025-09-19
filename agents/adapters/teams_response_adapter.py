"""
Teams-specific response adapter for formatting responses for Microsoft Teams.
This adapter handles Teams-specific UI components and formatting.
"""

import logging
from typing import Dict, Any, List, Optional

from botbuilder.core import TurnContext, MessageFactory
from botbuilder.schema import Activity, ActivityTypes, Attachment, CardAction, ActionTypes, TextFormatTypes

from services.rag_service import RAGResponse
from components.teams_components import TeamsComponents, TeamsCardConfig
from constants.teams_text import TeamsTextConstants


logger = logging.getLogger(__name__)


class TeamsResponseAdapter:
    """
    Teams-specific response adapter for formatting RAG responses.
    """
    
    def __init__(self, config: Optional[TeamsCardConfig] = None):
        self.config = config or TeamsCardConfig()
        self.teams_components = TeamsComponents()
        logger.info("TeamsResponseAdapter initialized")
    
    def format_rag_response(
        self,
        turn_context: TurnContext,
        rag_response: RAGResponse,
        conversation_data: Optional[Dict[str, Any]] = None
    ) -> Activity:
        """
        Format a RAG response for Teams with adaptive cards.
        """
        try:
            # Create adaptive card response
            card_json = self._create_rag_response_card(rag_response, conversation_data)
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            # Create activity with attachment
            activity = MessageFactory.attachment(attachment)
            activity.text = rag_response.answer  # Fallback text
            
            # Add suggested actions
            activity.suggested_actions = self._create_suggested_actions()
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting Teams RAG response: {e}")
            return MessageFactory.text(rag_response.answer)
    
    def format_text_response(
        self,
        turn_context: TurnContext,
        text: str,
        include_suggestions: bool = True
    ) -> Activity:
        """
        Format a simple text response for Teams.
        """
        activity = MessageFactory.text(text)
        
        if include_suggestions:
            activity.suggested_actions = self._create_suggested_actions()
        
        return activity
    
    def format_welcome_response(self, turn_context: TurnContext) -> Activity:
        """
        Format a welcome response for Teams.
        """
        try:
            card_json = self.teams_components.create_welcome_card()
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            activity = MessageFactory.attachment(attachment)
            activity.text = f"Welcome to {TeamsTextConstants.get_bot_name()}! {TeamsTextConstants.get_bot_description()}"
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting welcome response: {e}")
            return MessageFactory.text(TeamsTextConstants.format_welcome_fallback())
    
    def format_help_response(self, turn_context: TurnContext) -> Activity:
        """
        Format a help response for Teams.
        """
        try:
            card_json = self.teams_components.create_help_card()
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            activity = MessageFactory.attachment(attachment)
            activity.text = TeamsTextConstants.format_help_main_text()
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting help response: {e}")
            return MessageFactory.text(TeamsTextConstants.format_help_fallback())
    
    def format_error_response(
        self,
        turn_context: TurnContext,
        error_message: str
    ) -> Activity:
        """
        Format an error response for Teams.
        """
        try:
            card_json = self.teams_components.create_error_card(error_message)
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            activity = MessageFactory.attachment(attachment)
            activity.text = f"Error: {error_message}"
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting error response: {e}")
            return MessageFactory.text(f"Error: {error_message}")
    
    def format_loading_response(self, turn_context: TurnContext) -> Activity:
        """
        Format a loading response for Teams.
        """
        try:
            card_json = self.teams_components.create_loading_card()
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            activity = MessageFactory.attachment(attachment)
            activity.text = "Processing your request..."
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting loading response: {e}")
            return MessageFactory.text("Processing your request...")
    
    def format_file_upload_response(
        self,
        turn_context: TurnContext,
        file_name: str,
        file_type: str
    ) -> Activity:
        """
        Format a file upload response for Teams.
        """
        try:
            card_json = self.teams_components.create_file_upload_card(file_name, file_type)
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            activity = MessageFactory.attachment(attachment)
            activity.text = f"I've received your file: {file_name}"
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting file upload response: {e}")
            return MessageFactory.text(f"I've received your file: {file_name}")
    
    def format_quick_actions_response(self, turn_context: TurnContext) -> Activity:
        """
        Format a quick actions response for Teams.
        """
        try:
            card_json = self.teams_components.create_quick_actions_card()
            attachment = self.teams_components.create_attachment_from_card(card_json)
            
            activity = MessageFactory.attachment(attachment)
            activity.text = "Choose a quick action to get started:"
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting quick actions response: {e}")
            return MessageFactory.text(
                "Choose a quick action to get started:\n\n"
                "• Search Documents\n"
                "• Get Summary\n"
                "• Ask Question\n"
                "• Upload File"
            )
    
    def _create_rag_response_card(
        self,
        rag_response: RAGResponse,
        conversation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an adaptive card for RAG response.
        """
        card_json = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "🤖 RAG Assistant",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": rag_response.answer,
                    "wrap": True,
                    "size": "Medium",
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "💬 Ask Follow-up",
                    "data": {
                        "action": "follow_up",
                        "conversation_id": conversation_data.get("conversation_id", "") if isinstance(conversation_data, dict) else ""
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "🔍 Search Related",
                    "data": {
                        "action": "search_related",
                        "conversation_id": conversation_data.get("conversation_id", "") if isinstance(conversation_data, dict) else ""
                    },
                    "style": "default"
                },
                {
                    "type": "Action.Submit",
                    "title": "📋 Summarize",
                    "data": {
                        "action": "summarize",
                        "conversation_id": conversation_data.get("conversation_id", "") if isinstance(conversation_data, dict) else ""
                    },
                    "style": "default"
                }
            ]
        }
        
        # Add sources section if available and enabled
        if self.config.show_sources and rag_response.sources:
            sources_container = {
                "type": "Container",
                "style": "default",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "📚 Sources",
                        "weight": "Bolder",
                        "size": "Small",
                        "color": "Accent",
                        "spacing": "Medium"
                    }
                ]
            }
            
            for i, source in enumerate(rag_response.sources[:self.config.max_sources], 1):
                if isinstance(source, dict):
                    source_text = source.get('title', 'Unknown Source')
                    source_url = source.get('url', '')
                    
                    if source_url:
                        sources_container["items"].append({
                            "type": "TextBlock",
                            "text": f"{i}. [{source_text}]({source_url})",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        })
                    else:
                        sources_container["items"].append({
                            "type": "TextBlock",
                            "text": f"{i}. {source_text}",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        })
                else:
                    # Handle string sources
                    sources_container["items"].append({
                        "type": "TextBlock",
                        "text": f"{i}. {source}",
                        "wrap": True,
                        "size": "Small",
                        "spacing": "Small"
                    })
            
            card_json["body"].append(sources_container)
        
        # Add citations section if available and enabled
        if self.config.show_citations and rag_response.citations:
            citations_container = {
                "type": "Container",
                "style": "default",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "🔗 Citations",
                        "weight": "Bolder",
                        "size": "Small",
                        "color": "Accent",
                        "spacing": "Medium"
                    }
                ]
            }
            
            for i, citation in enumerate(rag_response.citations[:self.config.max_citations], 1):
                citations_container["items"].append({
                    "type": "TextBlock",
                    "text": f"{i}. {citation}",
                    "wrap": True,
                    "size": "Small",
                    "spacing": "Small"
                })
            
            card_json["body"].append(citations_container)
        
        # Add thoughts section if available and enabled
        if self.config.show_thoughts and rag_response.thoughts:
            thoughts_container = {
                "type": "Container",
                "style": "default",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "💭 Process",
                        "weight": "Bolder",
                        "size": "Small",
                        "color": "Accent",
                        "spacing": "Medium"
                    }
                ]
            }
            
            for thought in rag_response.thoughts[:self.config.max_thoughts]:
                thoughts_container["items"].append({
                    "type": "TextBlock",
                    "text": f"• {thought.get('title', 'Step')}: {thought.get('description', '')}",
                    "wrap": True,
                    "size": "Small",
                    "spacing": "Small"
                })
            
            card_json["body"].append(thoughts_container)
        
        # Add token usage if available and enabled
        if self.config.show_usage and rag_response.token_usage:
            usage_container = {
                "type": "Container",
                "style": "default",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "📊 Usage",
                        "weight": "Bolder",
                        "size": "Small",
                        "color": "Accent",
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"Tokens: {rag_response.token_usage.get('total_tokens', 'N/A')} (Prompt: {rag_response.token_usage.get('prompt_tokens', 'N/A')}, Completion: {rag_response.token_usage.get('completion_tokens', 'N/A')})",
                        "wrap": True,
                        "size": "Small",
                        "spacing": "Small"
                    }
                ]
            }
            card_json["body"].append(usage_container)
        
        return card_json
    
    def _create_suggested_actions(self) -> List[CardAction]:
        """
        Create suggested actions for Teams.
        """
        return self.teams_components.get_default_suggested_actions()