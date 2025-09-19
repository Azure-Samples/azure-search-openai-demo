"""
Teams-specific UI components and utilities.
This module contains reusable Teams UI components for the agent.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from botbuilder.schema import Attachment, CardAction, ActionTypes
from services.rag_service import RAGResponse


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
                            "text": "🤖 Welcome to RAG Assistant",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "I'm your AI-powered document search and chat assistant. I can help you find information from your documents and answer questions.",
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
                            "text": "🚀 What I can do:",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Search through your documents",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Answer questions about your content",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Provide summaries and insights",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Help with follow-up questions",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "💡 How to use:",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Mention me with @RAG Assistant",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Or just type your question directly",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Upload documents for me to search through",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🚀 Get Started",
                    "data": {
                        "action": "get_started"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "❓ Help",
                    "data": {
                        "action": "help"
                    },
                    "style": "default"
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
                            "text": "❓ RAG Assistant Help",
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
                            "text": "📚 Document Search",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Ask questions about your documents",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Search for specific information",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Get summaries and insights",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "💬 Chat Features",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Have conversations about your documents",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Ask follow-up questions",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Get detailed explanations",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "🔍 Example Questions",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• 'What are the main benefits mentioned in the policy document?'",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• 'Can you summarize the key points from the meeting notes?'",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• 'Find information about the new procedures'",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🚀 Try It Now",
                    "data": {
                        "action": "try_example"
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "📚 Upload Document",
                    "data": {
                        "action": "upload_document"
                    },
                    "style": "default"
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
                    "title": "❓ Get Help",
                    "data": {
                        "action": "help"
                    },
                    "style": "default"
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
                            "text": "🔄 Processing your request...",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Please wait while I search through your documents and generate a response.",
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