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
        Create an adaptive card response for Teams.
        """
        try:
            # Create adaptive card JSON
            card_json = {
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": rag_response.answer,
                        "wrap": True,
                        "size": "Medium"
                    }
                ],
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Ask Follow-up",
                        "data": {
                            "action": "follow_up",
                            "conversation_id": conversation_data.conversation_id
                        }
                    }
                ]
            }
            
            # Add sources if available
            if rag_response.sources:
                sources_text = "**Sources:**\n"
                for i, source in enumerate(rag_response.sources[:3], 1):
                    sources_text += f"{i}. {source.get('title', 'Unknown Source')}\n"
                
                card_json["body"].append({
                    "type": "TextBlock",
                    "text": sources_text,
                    "wrap": True,
                    "size": "Small",
                    "color": "Accent"
                })
            
            # Add citations if available
            if rag_response.citations:
                citations_text = "**Citations:**\n"
                for i, citation in enumerate(rag_response.citations[:3], 1):
                    citations_text += f"{i}. {citation}\n"
                
                card_json["body"].append({
                    "type": "TextBlock",
                    "text": citations_text,
                    "wrap": True,
                    "size": "Small",
                    "color": "Default"
                })
            
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