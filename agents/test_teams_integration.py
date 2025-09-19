"""
Test script for Teams integration features.
This script tests the Teams-specific functionality including adaptive cards,
mentions, file handling, and response formatting.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

from config.agent_config import AgentConfig
from services.rag_service import RAGService, RAGRequest, RAGResponse
from adapters.teams_response_adapter import TeamsResponseAdapter
from components.teams_components import TeamsComponents, TeamsCardConfig
from botbuilder.schema import Activity, ActivityTypes
from botbuilder.core import TurnContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockTurnContext:
    """Mock TurnContext for testing."""
    
    def __init__(self, activity: Activity):
        self.activity = activity
        self.channel_id = "msteams"
        self.conversation = activity.conversation
        self.from_property = activity.from_property
        self.recipient = activity.recipient


async def test_teams_components():
    """Test Teams components functionality."""
    logger.info("Testing Teams Components...")
    
    try:
        # Test welcome card
        welcome_card = TeamsComponents.create_welcome_card()
        assert welcome_card["type"] == "AdaptiveCard"
        assert "Welcome to RAG Assistant" in welcome_card["body"][0]["items"][0]["text"]
        logger.info("✅ Welcome card created successfully")
        
        # Test help card
        help_card = TeamsComponents.create_help_card()
        assert help_card["type"] == "AdaptiveCard"
        assert "RAG Assistant Help" in help_card["body"][0]["items"][0]["text"]
        logger.info("✅ Help card created successfully")
        
        # Test error card
        error_card = TeamsComponents.create_error_card("Test error message")
        assert error_card["type"] == "AdaptiveCard"
        assert "Test error message" in error_card["body"][1]["text"]
        logger.info("✅ Error card created successfully")
        
        # Test loading card
        loading_card = TeamsComponents.create_loading_card()
        assert loading_card["type"] == "AdaptiveCard"
        assert "Processing your request" in loading_card["body"][0]["items"][0]["text"]
        logger.info("✅ Loading card created successfully")
        
        # Test file upload card
        file_card = TeamsComponents.create_file_upload_card("test.pdf", "application/pdf")
        assert file_card["type"] == "AdaptiveCard"
        assert "test.pdf" in file_card["body"][1]["text"]
        logger.info("✅ File upload card created successfully")
        
        # Test quick actions card
        quick_actions_card = TeamsComponents.create_quick_actions_card()
        assert quick_actions_card["type"] == "AdaptiveCard"
        assert "Quick Actions" in quick_actions_card["body"][0]["items"][0]["text"]
        logger.info("✅ Quick actions card created successfully")
        
        logger.info("🎉 All Teams components tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Teams components test failed: {e}")
        raise


async def test_teams_response_adapter():
    """Test Teams response adapter functionality."""
    logger.info("Testing Teams Response Adapter...")
    
    try:
        # Create mock RAG response
        rag_response = RAGResponse(
            answer="This is a test response with comprehensive information about the topic.",
            sources=[
                {"title": "Source 1", "url": "https://example.com/source1"},
                {"title": "Source 2", "url": "https://example.com/source2"}
            ],
            citations=["Citation 1", "Citation 2"],
            thoughts=[
                {"title": "Query Analysis", "description": "Analyzed user query"},
                {"title": "Information Retrieval", "description": "Retrieved relevant documents"}
            ],
            token_usage={"total_tokens": 150, "prompt_tokens": 50, "completion_tokens": 100},
            model_info={"model": "gpt-4", "temperature": "0.3"}
        )
        
        # Create mock activity
        activity = Activity(
            type=ActivityTypes.message,
            text="Test message",
            from_property={"id": "user1", "name": "Test User"},
            recipient={"id": "bot1", "name": "RAG Assistant"},
            conversation={"id": "conv1"}
        )
        
        # Create mock turn context
        turn_context = MockTurnContext(activity)
        
        # Test response adapter
        adapter = TeamsResponseAdapter()
        
        # Test RAG response formatting
        response_activity = adapter.format_rag_response(turn_context, rag_response)
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        logger.info("✅ RAG response formatting successful")
        
        # Test text response formatting
        text_response = adapter.format_text_response(turn_context, "Simple text response")
        assert text_response.text == "Simple text response"
        assert text_response.suggested_actions is not None
        logger.info("✅ Text response formatting successful")
        
        # Test welcome response
        welcome_response = adapter.format_welcome_response(turn_context)
        assert welcome_response.attachments is not None
        assert len(welcome_response.attachments) > 0
        logger.info("✅ Welcome response formatting successful")
        
        # Test help response
        help_response = adapter.format_help_response(turn_context)
        assert help_response.attachments is not None
        assert len(help_response.attachments) > 0
        logger.info("✅ Help response formatting successful")
        
        # Test error response
        error_response = adapter.format_error_response(turn_context, "Test error")
        assert error_response.attachments is not None
        assert len(error_response.attachments) > 0
        logger.info("✅ Error response formatting successful")
        
        # Test loading response
        loading_response = adapter.format_loading_response(turn_context)
        assert loading_response.attachments is not None
        assert len(loading_response.attachments) > 0
        logger.info("✅ Loading response formatting successful")
        
        # Test file upload response
        file_response = adapter.format_file_upload_response(turn_context, "test.pdf", "application/pdf")
        assert file_response.attachments is not None
        assert len(file_response.attachments) > 0
        logger.info("✅ File upload response formatting successful")
        
        # Test quick actions response
        quick_actions_response = adapter.format_quick_actions_response(turn_context)
        assert quick_actions_response.attachments is not None
        assert len(quick_actions_response.attachments) > 0
        logger.info("✅ Quick actions response formatting successful")
        
        logger.info("🎉 All Teams response adapter tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Teams response adapter test failed: {e}")
        raise


async def test_adaptive_card_configuration():
    """Test adaptive card configuration options."""
    logger.info("Testing Adaptive Card Configuration...")
    
    try:
        # Test default configuration
        default_config = TeamsCardConfig()
        assert default_config.show_sources == True
        assert default_config.show_citations == True
        assert default_config.show_thoughts == False
        assert default_config.show_usage == False
        assert default_config.max_sources == 3
        assert default_config.max_citations == 3
        assert default_config.max_thoughts == 2
        assert default_config.include_actions == True
        logger.info("✅ Default configuration test passed")
        
        # Test custom configuration
        custom_config = TeamsCardConfig(
            show_sources=False,
            show_citations=True,
            show_thoughts=True,
            show_usage=True,
            max_sources=5,
            max_citations=2,
            max_thoughts=1,
            include_actions=False
        )
        assert custom_config.show_sources == False
        assert custom_config.show_citations == True
        assert custom_config.show_thoughts == True
        assert custom_config.show_usage == True
        assert custom_config.max_sources == 5
        assert custom_config.max_citations == 2
        assert custom_config.max_thoughts == 1
        assert custom_config.include_actions == False
        logger.info("✅ Custom configuration test passed")
        
        logger.info("🎉 All adaptive card configuration tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Adaptive card configuration test failed: {e}")
        raise


async def test_teams_integration():
    """Test complete Teams integration."""
    logger.info("Testing Complete Teams Integration...")
    
    try:
        # Load configuration
        config = AgentConfig.from_environment()
        
        # Set dummy values for testing
        config.app_id = "test-app-id"
        config.app_password = "test-app-password"
        config.tenant_id = "test-tenant-id"
        config.client_id = "test-client-id"
        config.client_secret = "test-client-secret"
        
        config.validate()
        
        # Initialize RAG service
        rag_service = RAGService(config)
        await rag_service.initialize()
        
        # Test RAG service with Teams-specific request
        request = RAGRequest(
            message="What are the main benefits mentioned in the policy document?",
            user_id="teams_user_1",
            channel_id="msteams",
            conversation_history=[]
        )
        
        # Test non-streaming response
        response = await rag_service.process_query(request)
        assert response.answer
        assert len(response.sources) > 0 or len(response.citations) > 0
        logger.info("✅ RAG service integration test passed")
        
        # Test streaming response
        stream_response = ""
        async for chunk in rag_service.process_query_stream(request):
            if chunk.get("type") == "content":
                stream_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                raise Exception(f"Streaming error: {chunk.get('content')}")
        
        assert stream_response
        logger.info("✅ RAG service streaming integration test passed")
        
        # Test Teams response formatting with real RAG response
        activity = Activity(
            type=ActivityTypes.message,
            text="What are the main benefits?",
            from_property={"id": "teams_user_1", "name": "Teams User"},
            recipient={"id": "bot1", "name": "RAG Assistant"},
            conversation={"id": "teams_conv_1"}
        )
        
        turn_context = MockTurnContext(activity)
        adapter = TeamsResponseAdapter()
        
        teams_response = adapter.format_rag_response(turn_context, response)
        assert teams_response.attachments is not None
        assert len(teams_response.attachments) > 0
        assert teams_response.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        logger.info("✅ Teams response formatting integration test passed")
        
        await rag_service.close()
        logger.info("🎉 All Teams integration tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Teams integration test failed: {e}")
        raise


async def main():
    """Run all Teams integration tests."""
    logger.info("Starting Teams integration tests...")
    
    try:
        # Test 1: Teams Components
        await test_teams_components()
        
        # Test 2: Teams Response Adapter
        await test_teams_response_adapter()
        
        # Test 3: Adaptive Card Configuration
        await test_adaptive_card_configuration()
        
        # Test 4: Complete Integration
        await test_teams_integration()
        
        logger.info("🎉 All Teams integration tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Teams integration tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())