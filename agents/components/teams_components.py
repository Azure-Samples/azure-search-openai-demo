"""
Teams-specific UI components and utilities.
This module contains reusable Teams UI components for the agent.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from botbuilder.schema import Attachment, CardAction, ActionTypes
from services.rag_service import RAGResponse
from constants.teams_text import TeamsTextConstants


logger = logging.getLogger(__name__)


@dataclass
class TeamsCardConfig:
    """Configuration for Teams adaptive cards."""
    show_sources: bool = True
    show_citations: bool = True
    show_thoughts: bool = False
    show_usage: bool = False
    max_sources: int = 3
    max_citations: int = 3
    max_thoughts: int = 2
    include_actions: bool = True


class TeamsComponents:
    """
    Teams-specific UI components for the agent.
    """
    
    @staticmethod
    def create_welcome_card() -> Dict[str, Any]:
        """Create a welcome card for new users."""
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.format_welcome_title(),
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": TeamsTextConstants.format_welcome_description(),
                    "wrap": True,
                    "size": "Medium",
                    "spacing": "Medium"
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.CAPABILITIES_TITLE,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        }
                    ] + [
                        {
                            "type": "TextBlock",
                            "text": capability,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                        for capability in TeamsTextConstants.CAPABILITIES
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.USAGE_TITLE,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        }
                    ] + [
                        {
                            "type": "TextBlock",
                            "text": instruction,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                        for instruction in TeamsTextConstants.format_usage_instructions()
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": TeamsTextConstants.ACTION_GET_STARTED,
                    "data": {
                        "action": "get_started"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": TeamsTextConstants.ACTION_HELP,
                    "data": {
                        "action": "help"
                    }
                }
            ]
        }
    
    @staticmethod
    def create_help_card() -> Dict[str, Any]:
        """Create a help card with usage instructions."""
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.format_help_title(),
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.STRUCTURAL_ANALYSIS_TITLE,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        }
                    ] + [
                        {
                            "type": "TextBlock",
                            "text": item,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                        for item in TeamsTextConstants.STRUCTURAL_ANALYSIS_ITEMS
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.TECHNICAL_CHAT_TITLE,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        }
                    ] + [
                        {
                            "type": "TextBlock",
                            "text": item,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                        for item in TeamsTextConstants.TECHNICAL_CHAT_ITEMS
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.EXAMPLE_QUESTIONS_TITLE,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        }
                    ] + [
                        {
                            "type": "TextBlock",
                            "text": question,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                        for question in TeamsTextConstants.EXAMPLE_QUESTIONS
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": TeamsTextConstants.ACTION_TRY_NOW,
                    "data": {
                        "action": "try_example"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": TeamsTextConstants.ACTION_UPLOAD_DRAWING,
                    "data": {
                        "action": "upload_document"
                    }
                }
            ]
        }
    
    @staticmethod
    def create_error_card(error_message: str) -> Dict[str, Any]:
        """Create an error card for displaying errors."""
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "attention",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "⚠️ Error",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Attention"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": error_message,
                    "wrap": True,
                    "size": "Medium",
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🔄 Try Again",
                    "data": {
                        "action": "retry"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": TeamsTextConstants.ACTION_HELP,
                    "data": {
                        "action": "help"
                    }
                }
            ]
        }
    
    @staticmethod
    def create_loading_card() -> Dict[str, Any]:
        """Create a loading card while processing requests."""
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.LOADING_TITLE,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent"
                        },
                        {
                            "type": "TextBlock",
                            "text": TeamsTextConstants.LOADING_MESSAGE,
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Medium"
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def create_file_upload_card(file_name: str, file_type: str) -> Dict[str, Any]:
        """Create a card for file upload confirmation."""
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "📎 File Uploaded",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": f"I've received your file: **{file_name}**",
                    "wrap": True,
                    "size": "Medium",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": f"File type: {file_type}",
                    "wrap": True,
                    "size": "Small",
                    "spacing": "Small"
                },
                {
                    "type": "TextBlock",
                    "text": "I can help you search through this document and answer questions about its content. What would you like to know?",
                    "wrap": True,
                    "size": "Medium",
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🔍 Search Document",
                    "data": {
                        "action": "search_document",
                        "file_name": file_name
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "📋 Summarize Document",
                    "data": {
                        "action": "summarize_document",
                        "file_name": file_name
                    },
                    "style": "default"
                }
            ]
        }
    
    @staticmethod
    def create_quick_actions_card() -> Dict[str, Any]:
        """Create a card with quick action buttons."""
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "⚡ Quick Actions",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "Choose a quick action to get started:",
                    "wrap": True,
                    "size": "Medium",
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🔍 Search Documents",
                    "data": {
                        "action": "quick_search"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "📋 Get Summary",
                    "data": {
                        "action": "quick_summary"
                    },
                    "style": "default"
                },
                {
                    "type": "Action.Submit",
                    "title": "❓ Ask Question",
                    "data": {
                        "action": "quick_question"
                    },
                    "style": "default"
                },
                {
                    "type": "Action.Submit",
                    "title": "📚 Upload File",
                    "data": {
                        "action": "quick_upload"
                    },
                    "style": "default"
                }
            ]
        }
    
    @staticmethod
    def create_attachment_from_card(card_json: Dict[str, Any]) -> Attachment:
        """Create an attachment from a card JSON."""
        return Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=card_json
        )
    
    @staticmethod
    def create_suggested_actions(actions: List[str]) -> List[CardAction]:
        """Create suggested actions for Teams."""
        return [
            CardAction(
                type=ActionTypes.im_back,
                title=action,
                value=action
            )
            for action in actions
        ]