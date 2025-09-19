"""
Teams-specific handler for Microsoft 365 Agent.
This handler provides Teams-specific functionality and message formatting.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from botbuilder.core import TurnContext, MessageFactory
from botbuilder.schema import Activity, Attachment, CardAction, ActionTypes
from botbuilder.adapters.teams import TeamsActivityHandler, TeamsInfo

from services.rag_service import RAGService, RAGRequest, RAGResponse
from services.auth_service import AuthService
from adapters.response_adapter import ResponseAdapter
from adapters.teams_response_adapter import TeamsResponseAdapter
from components.teams_components import TeamsComponents, TeamsCardConfig


logger = logging.getLogger(__name__)


@dataclass
class ConversationData:
    """Data stored for each conversation."""
    conversation_id: str
    user_id: str
    channel_id: str
    message_count: int = 0
    last_activity: Optional[str] = None


class TeamsHandler(TeamsActivityHandler):
    """
    Teams-specific handler that extends the base message handler
    with Teams-specific functionality like adaptive cards, mentions, and file handling.
    """
    
    def __init__(self, rag_service: RAGService, auth_service: AuthService):
        super().__init__()
        self.rag_service = rag_service
        self.auth_service = auth_service
        self.response_adapter = ResponseAdapter()
        self.teams_response_adapter = TeamsResponseAdapter()
        self.teams_components = TeamsComponents()
    
    async def handle_message(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData,
        user_data: Dict[str, Any],
        auth_claims: Dict[str, Any]
    ) -> Optional[Activity]:
        """
        Handle an incoming Teams message and generate a response.
        """
        try:
            # Check if this is an adaptive card action
            if turn_context.activity.value:
                return await self._handle_adaptive_card_action(
                    turn_context, conversation_data, user_data, auth_claims
                )
            
            # Check if the bot was mentioned
            if await self._is_bot_mentioned(turn_context):
                # Remove the mention from the message
                message_text = await self._remove_mention(turn_context)
            else:
                message_text = turn_context.activity.text or ""
            
            if not message_text.strip():
                return await self._create_mention_reminder(turn_context)
            
            # Get conversation history from user data
            conversation_history = user_data.get("conversation_history", [])
            
            # Create RAG request
            rag_request = RAGRequest(
                message=message_text,
                conversation_history=conversation_history,
                user_id=conversation_data.user_id,
                channel_id=conversation_data.channel_id,
                context={
                    "auth_claims": auth_claims,
                    "conversation_id": conversation_data.conversation_id,
                    "message_count": conversation_data.message_count,
                    "teams_context": await self._get_teams_context(turn_context)
                }
            )
            
            # Process the request with RAG service
            rag_response = await self.rag_service.process_query(rag_request)
            
            # Update conversation history
            conversation_history.append({
                "role": "user",
                "content": message_text
            })
            conversation_history.append({
                "role": "assistant",
                "content": rag_response.answer
            })
            
            # Keep only the last 10 exchanges to manage context length
            if len(conversation_history) > 20:  # 10 user + 10 assistant messages
                conversation_history = conversation_history[-20:]
            
            user_data["conversation_history"] = conversation_history
            
            # Format response for Teams
            response_activity = await self._format_teams_response(
                turn_context, rag_response, conversation_data
            )
            
            return response_activity
            
        except Exception as e:
            logger.error(f"Error handling Teams message: {e}")
            return MessageFactory.text(
                "I'm sorry, I encountered an error processing your request. Please try again."
            )
    
    async def _handle_adaptive_card_action(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData,
        user_data: Dict[str, Any],
        auth_claims: Dict[str, Any]
    ) -> Optional[Activity]:
        """
        Handle adaptive card button actions.
        """
        try:
            action_data = turn_context.activity.value
            action_type = action_data.get("action", "")
            
            if action_type == "follow_up":
                return await self._handle_follow_up_action(
                    turn_context, conversation_data, user_data, auth_claims
                )
            elif action_type == "search_related":
                return await self._handle_search_related_action(
                    turn_context, conversation_data, user_data, auth_claims
                )
            elif action_type == "summarize":
                return await self._handle_summarize_action(
                    turn_context, conversation_data, user_data, auth_claims
                )
            else:
                return MessageFactory.text(
                    f"I received an action '{action_type}' but I'm not sure how to handle it. Please try asking me a question directly."
                )
                
        except Exception as e:
            logger.error(f"Error handling adaptive card action: {e}")
            return MessageFactory.text(
                "I encountered an error processing your action. Please try asking me a question directly."
            )
    
    async def _handle_follow_up_action(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData,
        user_data: Dict[str, Any],
        auth_claims: Dict[str, Any]
    ) -> Activity:
        """Handle follow-up action."""
        return MessageFactory.text(
            "I'd be happy to provide more details! What specific aspect would you like me to elaborate on? You can ask me to:\n\n"
            "• Explain any part in more detail\n"
            "• Provide examples\n"
            "• Compare different options\n"
            "• Answer related questions\n\n"
            "Just type your question and I'll help you out!"
        )
    
    async def _handle_search_related_action(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData,
        user_data: Dict[str, Any],
        auth_claims: Dict[str, Any]
    ) -> Activity:
        """Handle search related action."""
        return MessageFactory.text(
            "I can help you find more information about this topic! Try asking me:\n\n"
            "• 'What are the requirements for...?'\n"
            "• 'How do I apply for...?'\n"
            "• 'What are the steps to...?'\n"
            "• 'Tell me more about...'\n\n"
            "Or just describe what you're looking for and I'll search through the documents for you!"
        )
    
    async def _handle_summarize_action(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData,
        user_data: Dict[str, Any],
        auth_claims: Dict[str, Any]
    ) -> Activity:
        """Handle summarize action."""
        return MessageFactory.text(
            "I can help you summarize information! You can ask me to:\n\n"
            "• 'Summarize the key points'\n"
            "• 'Give me a brief overview'\n"
            "• 'What are the main takeaways?'\n"
            "• 'Create a bullet point summary'\n\n"
            "Just let me know what you'd like me to summarize!"
        )
    
    async def _is_bot_mentioned(self, turn_context: TurnContext) -> bool:
        """Check if the bot was mentioned in the message."""
        try:
            # Check if the bot is mentioned in the activity
            if hasattr(turn_context.activity, 'entities') and turn_context.activity.entities:
                for entity in turn_context.activity.entities:
                    if entity.type == "mention" and entity.mentioned:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking bot mention: {e}")
            return False
    
    async def _remove_mention(self, turn_context: TurnContext) -> str:
        """Remove bot mention from the message text."""
        try:
            message_text = turn_context.activity.text or ""
            
            # Simple mention removal - in production, you'd want more sophisticated parsing
            if "<at>" in message_text and "</at>" in message_text:
                # Remove the mention tags and content
                import re
                message_text = re.sub(r'<at>.*?</at>', '', message_text).strip()
            
            return message_text
        except Exception as e:
            logger.warning(f"Error removing mention: {e}")
            return turn_context.activity.text or ""
    
    async def _get_teams_context(self, turn_context: TurnContext) -> Dict[str, Any]:
        """Get Teams-specific context information."""
        try:
            context = {
                "channel_id": turn_context.activity.channel_id,
                "conversation_id": turn_context.activity.conversation.id,
                "user_id": turn_context.activity.from_property.id,
                "user_name": turn_context.activity.from_property.name,
                "tenant_id": turn_context.activity.conversation.tenant_id if hasattr(turn_context.activity.conversation, 'tenant_id') else None
            }
            
            # Try to get additional Teams context
            try:
                teams_info = await TeamsInfo.get_team_details(turn_context)
                context["team_id"] = teams_info.id
                context["team_name"] = teams_info.name
            except Exception:
                # Not in a team context
                pass
            
            return context
            
        except Exception as e:
            logger.warning(f"Error getting Teams context: {e}")
            return {}
    
    async def _format_teams_response(
        self,
        turn_context: TurnContext,
        rag_response: RAGResponse,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Format the RAG response specifically for Teams.
        """
        try:
            # Create adaptive card for rich response
            if rag_response.sources or rag_response.citations:
                return await self._create_adaptive_card_response(
                    turn_context, rag_response, conversation_data
                )
            else:
                # Simple text response
                return MessageFactory.text(rag_response.answer)
                
        except Exception as e:
            logger.error(f"Error formatting Teams response: {e}")
            return MessageFactory.text(rag_response.answer)
    
    async def _create_adaptive_card_response(
        self,
        turn_context: TurnContext,
        rag_response: RAGResponse,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Create an adaptive card response for Teams with rich formatting.
        """
        try:
            # Create adaptive card JSON with enhanced styling
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
                            "conversation_id": conversation_data.conversation_id
                        },
                        "style": "positive"
                    },
                    {
                        "type": "Action.Submit",
                        "title": "🔍 Search Related",
                        "data": {
                            "action": "search_related",
                            "conversation_id": conversation_data.conversation_id
                        },
                        "style": "default"
                    },
                    {
                        "type": "Action.Submit",
                        "title": "📋 Summarize",
                        "data": {
                            "action": "summarize",
                            "conversation_id": conversation_data.conversation_id
                        },
                        "style": "default"
                    }
                ]
            }
            
            # Add sources section if available
            if rag_response.sources:
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
                
                for i, source in enumerate(rag_response.sources[:3], 1):
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
                
                card_json["body"].append(sources_container)
            
            # Add citations section if available
            if rag_response.citations:
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
                
                for i, citation in enumerate(rag_response.citations[:3], 1):
                    citations_container["items"].append({
                        "type": "TextBlock",
                        "text": f"{i}. {citation}",
                        "wrap": True,
                        "size": "Small",
                        "spacing": "Small"
                    })
                
                card_json["body"].append(citations_container)
            
            # Add thoughts section if available (for transparency)
            if rag_response.thoughts:
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
                
                for thought in rag_response.thoughts[:2]:  # Limit to 2 thoughts
                    thoughts_container["items"].append({
                        "type": "TextBlock",
                        "text": f"• {thought.get('title', 'Step')}: {thought.get('description', '')}",
                        "wrap": True,
                        "size": "Small",
                        "spacing": "Small"
                    })
                
                card_json["body"].append(thoughts_container)
            
            # Add token usage if available
            if rag_response.token_usage:
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
            
            # Create attachment
            attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=card_json
            )
            
            # Create activity with attachment
            activity = MessageFactory.attachment(attachment)
            activity.text = rag_response.answer  # Fallback text
            
            return activity
            
        except Exception as e:
            logger.error(f"Error creating adaptive card: {e}")
            return MessageFactory.text(rag_response.answer)
    
    async def _create_mention_reminder(self, turn_context: TurnContext) -> Activity:
        """Create a reminder to mention the bot."""
        reminder_text = """
👋 Hi! I'm your AI assistant. To ask me a question, please mention me using @RAG Assistant or type your question directly.

**What I can help with:**
• Search through your documents
• Answer questions about your content
• Provide summaries and insights

Try asking me something like: "What are the main points in the latest policy document?"
        """
        
        return MessageFactory.text(reminder_text)
    
    async def handle_file_upload(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Handle file uploads in Teams.
        """
        try:
            # Check if there are attachments
            if turn_context.activity.attachments:
                file_info = []
                for attachment in turn_context.activity.attachments:
                    file_info.append(f"• {attachment.name} ({attachment.content_type})")
                
                response_text = f"""
📎 I see you've uploaded {len(turn_context.activity.attachments)} file(s):

{chr(10).join(file_info)}

I can help you search through these documents once they're processed. You can ask me questions about their content, or I can provide summaries and insights.

**What would you like to know about these files?**
                """
                
                return MessageFactory.text(response_text)
            else:
                return MessageFactory.text("I don't see any files attached. Please try uploading a file and I'll help you with it.")
                
        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
            return MessageFactory.text("I encountered an error processing your file upload. Please try again.")
    
    async def handle_help_request(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Handle help requests in Teams.
        """
        help_text = """
🤖 **RAG Assistant Help**

I'm your AI-powered document search and chat assistant. Here's what I can do:

**📚 Document Search**
- Ask questions about your documents
- Search for specific information
- Get summaries and insights

**💬 Chat Features**
- Have conversations about your documents
- Ask follow-up questions
- Get detailed explanations

**🔍 How to Use**
- Mention me with @RAG Assistant or just type your question
- I'll search through your documents and provide answers
- I can cite sources and provide context

**❓ Examples**
- "What are the main benefits mentioned in the policy document?"
- "Can you summarize the key points from the meeting notes?"
- "Find information about the new procedures"

**📎 File Uploads**
- Upload documents and I'll help you search through them
- Ask questions about uploaded files
- Get insights and summaries

Type your question or mention me to get started!
        """
        
        return MessageFactory.text(help_text)