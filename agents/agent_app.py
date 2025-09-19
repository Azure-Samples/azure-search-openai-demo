"""
Main Microsoft 365 Agent Application.
This module contains the core agent application that integrates with Microsoft 365 Agents SDK.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from botbuilder.core import (
    ActivityHandler,
    TurnContext,
    MessageFactory,
    ConversationState,
    UserState,
    MemoryStorage,
)
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    ChannelAccount,
    ConversationReference,
    ResourceResponse,
)
from botbuilder.adapters import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.adapters.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.adapters.azure import AzureServiceClientCredentials

from config.agent_config import AgentConfig
from services.rag_service import RAGService
from services.auth_service import AuthService
from handlers.message_handler import MessageHandler
from handlers.teams_handler import TeamsHandler
from adapters.response_adapter import ResponseAdapter


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConversationData:
    """Data stored for each conversation."""
    conversation_id: str
    user_id: str
    channel_id: str
    message_count: int = 0
    last_activity: Optional[str] = None


class RAGAgent(ActivityHandler):
    """
    Main RAG Agent that handles Microsoft 365 activities.
    Integrates with existing RAG services while providing Microsoft 365 channel support.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        rag_service: RAGService,
        auth_service: AuthService,
        conversation_state: ConversationState,
        user_state: UserState,
    ):
        super().__init__()
        self.config = config
        self.rag_service = rag_service
        self.auth_service = auth_service
        self.conversation_state = conversation_state
        self.user_state = user_state
        
        # Initialize handlers
        self.message_handler = MessageHandler(rag_service, auth_service)
        self.teams_handler = TeamsHandler(rag_service, auth_service)
        self.response_adapter = ResponseAdapter()
        
        # Accessor for conversation data
        self.conversation_data_accessor = self.conversation_state.create_property("ConversationData")
        self.user_data_accessor = self.user_state.create_property("UserData")
    
    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """Handle incoming message activities."""
        try:
            # Get conversation and user data
            conversation_data = await self.conversation_data_accessor.get(turn_context, ConversationData)
            user_data = await self.user_data_accessor.get(turn_context, dict)
            
            # Initialize conversation data if needed
            if not conversation_data:
                conversation_data = ConversationData(
                    conversation_id=turn_context.activity.conversation.id,
                    user_id=turn_context.activity.from_property.id,
                    channel_id=turn_context.activity.channel_id,
                )
            
            # Update conversation data
            conversation_data.message_count += 1
            conversation_data.last_activity = turn_context.activity.text
            
            # Get user authentication claims
            auth_claims = await self.auth_service.get_user_claims(turn_context)
            
            # Process the message based on channel
            if turn_context.activity.channel_id == "msteams":
                response = await self.teams_handler.handle_message(
                    turn_context, conversation_data, user_data, auth_claims
                )
            else:
                response = await self.message_handler.handle_message(
                    turn_context, conversation_data, user_data, auth_claims
                )
            
            # Send response
            if response:
                await turn_context.send_activity(response)
            
            # Save state
            await self.conversation_state.save_changes(turn_context)
            await self.user_state.save_changes(turn_context)
            
        except Exception as e:
            logger.error(f"Error handling message activity: {e}")
            await turn_context.send_activity(
                MessageFactory.text("I'm sorry, I encountered an error processing your request. Please try again.")
            )
    
    async def on_members_added_activity(
        self, members_added: list[ChannelAccount], turn_context: TurnContext
    ) -> None:
        """Handle when members are added to the conversation."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_message = (
                    f"Welcome {member.name}! I'm your AI-powered document search assistant. "
                    f"I can help you find information from your documents and answer questions. "
                    f"Just ask me anything!"
                )
                await turn_context.send_activity(MessageFactory.text(welcome_message))
    
    async def on_typing_activity(self, turn_context: TurnContext) -> None:
        """Handle typing indicators."""
        if self.config.enable_typing_indicator:
            # Echo typing indicator back
            typing_activity = Activity(
                type=ActivityTypes.typing,
                channel_id=turn_context.activity.channel_id,
                conversation=turn_context.activity.conversation,
                recipient=turn_context.activity.from_property,
            )
            await turn_context.send_activity(typing_activity)
    
    async def on_end_of_conversation_activity(self, turn_context: TurnContext) -> None:
        """Handle end of conversation."""
        logger.info(f"Conversation ended: {turn_context.activity.conversation.id}")
        await self.conversation_state.clear(turn_context)
        await self.user_state.clear(turn_context)


class AgentApplication:
    """
    Main application class that sets up and runs the Microsoft 365 Agent.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.config.validate()
        
        # Initialize services
        self.rag_service = RAGService(config)
        self.auth_service = AuthService(config)
        
        # Initialize state management
        memory_storage = MemoryStorage()
        self.conversation_state = ConversationState(memory_storage)
        self.user_state = UserState(memory_storage)
        
        # Initialize the agent
        self.agent = RAGAgent(
            config=config,
            rag_service=self.rag_service,
            auth_service=self.auth_service,
            conversation_state=self.conversation_state,
            user_state=self.user_state,
        )
        
        # Initialize adapter
        self.adapter = self._create_adapter()
    
    def _create_adapter(self) -> BotFrameworkAdapter:
        """Create the Bot Framework adapter."""
        settings = BotFrameworkAdapterSettings(
            app_id=self.config.app_id,
            app_password=self.config.app_password,
        )
        
        adapter = BotFrameworkAdapter(settings)
        
        # Add error handler
        async def on_error(context: TurnContext, error: Exception) -> None:
            logger.error(f"Error occurred: {error}")
            await context.send_activity(
                MessageFactory.text("I'm sorry, I encountered an error. Please try again.")
            )
        
        adapter.on_turn_error = on_error
        
        return adapter
    
    async def process_activity(self, activity: Activity) -> ResourceResponse:
        """Process an incoming activity."""
        return await self.adapter.process_activity(activity, "", self.agent.on_turn)
    
    def get_adapter(self) -> BotFrameworkAdapter:
        """Get the Bot Framework adapter."""
        return self.adapter