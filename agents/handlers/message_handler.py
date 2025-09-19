"""
Message Handler for Microsoft 365 Agent.
This handler processes incoming messages and generates responses.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from botbuilder.core import TurnContext, MessageFactory
from botbuilder.schema import Activity

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


class MessageHandler:
    """
    Handler for processing incoming messages and generating responses.
    This handler works with the RAG service to provide intelligent responses.
    """
    
    def __init__(self, rag_service: RAGService, auth_service: AuthService):
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
        Handle an incoming message and generate a response.
        """
        try:
            # Extract message text
            message_text = turn_context.activity.text or ""
            
            if not message_text.strip():
                return MessageFactory.text("I didn't receive any message. Please try again.")
            
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
                    "message_count": conversation_data.message_count
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
            
            # Format response for the channel
            response_activity = await self._format_response(
                turn_context, rag_response, conversation_data
            )
            
            return response_activity
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return MessageFactory.text(
                "I'm sorry, I encountered an error processing your request. Please try again."
            )
    
    async def _format_response(
        self,
        turn_context: TurnContext,
        rag_response: RAGResponse,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Format the RAG response for the specific channel.
        """
        try:
            # Use the response adapter to format the response
            formatted_response = await self.response_adapter.format_response(
                rag_response, turn_context.activity.channel_id
            )
            
            # Create the activity
            activity = MessageFactory.text(formatted_response["text"])
            
            # Add additional properties if available
            if "attachments" in formatted_response:
                activity.attachments = formatted_response["attachments"]
            
            if "suggested_actions" in formatted_response:
                activity.suggested_actions = formatted_response["suggested_actions"]
            
            return activity
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return MessageFactory.text(rag_response.answer)
    
    async def handle_typing_indicator(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData
    ) -> None:
        """
        Handle typing indicators.
        """
        try:
            # Send typing indicator back
            typing_activity = Activity(
                type="typing",
                channel_id=turn_context.activity.channel_id,
                conversation=turn_context.activity.conversation,
                recipient=turn_context.activity.from_property,
            )
            await turn_context.send_activity(typing_activity)
            
        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}")
    
    async def handle_help_request(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Handle help requests.
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
- Just type your question naturally
- I'll search through your documents and provide answers
- I can cite sources and provide context

**❓ Examples**
- "What are the main benefits mentioned in the policy document?"
- "Can you summarize the key points from the meeting notes?"
- "Find information about the new procedures"

Type your question to get started!
        """
        
        return MessageFactory.text(help_text)
    
    async def handle_unknown_command(
        self,
        turn_context: TurnContext,
        conversation_data: ConversationData
    ) -> Activity:
        """
        Handle unknown commands or unclear messages.
        """
        unknown_text = """
I'm not sure what you're looking for. Here are some things I can help with:

• Ask questions about your documents
• Search for specific information
• Get summaries and insights
• Have conversations about your content

Try asking me a specific question, or type "help" for more information.
        """
        
        return MessageFactory.text(unknown_text)