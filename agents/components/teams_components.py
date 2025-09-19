"""
Teams-specific UI components and utilities.
This module contains reusable Teams UI components for the agent.
"""

import logging
import os
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
        # Get bot configuration from environment
        bot_name = os.getenv("AGENT_NAME", "Structural Engineering Assistant")
        bot_description = os.getenv("AGENT_DESCRIPTION", "AI-powered structural engineering document search and analysis assistant")
        
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
                            "text": f"🏗️ Welcome to {bot_name}",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Accent"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": f"{bot_description}. I can help you analyze structural engineering documents, answer technical questions, and provide insights from your project files.",
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
                            "text": "🔧 What I can do:",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Analyze structural drawings and specifications",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Answer questions about building codes and standards",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Review calculations and design reports",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Provide technical insights and recommendations",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Help with material specifications and load calculations",
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
                            "text": f"• Mention me with @{bot_name}",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Upload structural drawings, specs, or reports",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Ask technical questions about your projects",
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
                    }
                }
            ]
        }
    
    @staticmethod
    def create_help_card() -> Dict[str, Any]:
        """Create a help card with usage instructions."""
        # Get bot configuration from environment
        bot_name = os.getenv("AGENT_NAME", "Structural Engineering Assistant")
        
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
                            "text": f"❓ {bot_name} Help",
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
                            "text": "📐 Structural Analysis",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Analyze structural drawings and specifications",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Review load calculations and design reports",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Check compliance with building codes",
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
                            "text": "💬 Technical Chat",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                            "spacing": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Ask questions about structural engineering concepts",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Get explanations of design principles",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Request material and code recommendations",
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
                            "text": "• 'What are the load requirements for this beam design?'",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• 'Can you review this foundation calculation?'",
                            "wrap": True,
                            "size": "Small",
                            "spacing": "Small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• 'What building code applies to this steel structure?'",
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
                    "title": "📐 Upload Drawing",
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