"""
Pytest tests for Teams response adapter functionality.
Tests Teams-specific response formatting and adaptation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from botbuilder.schema import Activity, ActivityTypes

from adapters.teams_response_adapter import TeamsResponseAdapter
from components.teams_components import TeamsCardConfig
from services.rag_service import RAGResponse
from constants.teams_text import TeamsTextConstants


class MockTurnContext:
    """Mock TurnContext for testing."""
    
    def __init__(self, activity: Activity):
        self.activity = activity
        self.channel_id = "msteams"
        self.conversation = activity.conversation
        self.from_property = activity.from_property
        self.recipient = activity.recipient


class TestTeamsResponseAdapter:
    """Test cases for TeamsResponseAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create a TeamsResponseAdapter instance for testing."""
        return TeamsResponseAdapter()
    
    @pytest.fixture
    def mock_turn_context(self):
        """Create a mock TurnContext for testing."""
        activity = Activity(
            type=ActivityTypes.message,
            text="Test message",
            from_property={"id": "user1", "name": "Test User"},
            recipient={"id": "bot1", "name": "RAG Assistant"},
            conversation={"id": "conv1"}
        )
        return MockTurnContext(activity)
    
    @pytest.fixture
    def mock_rag_response(self):
        """Create a mock RAGResponse for testing."""
        return RAGResponse(
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
    
    def test_format_rag_response(self, adapter, mock_turn_context, mock_rag_response):
        """Test RAG response formatting."""
        response_activity = adapter.format_rag_response(mock_turn_context, mock_rag_response)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        assert response_activity.text == mock_rag_response.answer
        
        # Check adaptive card content
        card_content = response_activity.attachments[0].content
        assert card_content["type"] == "AdaptiveCard"
        assert card_content["version"] == "1.4"
        assert len(card_content["body"]) > 0
        assert len(card_content["actions"]) > 0
    
    def test_format_text_response(self, adapter, mock_turn_context):
        """Test text response formatting."""
        text = "Simple text response"
        response_activity = adapter.format_text_response(mock_turn_context, text)
        
        assert response_activity.text == text
        assert response_activity.suggested_actions is not None
        assert len(response_activity.suggested_actions) > 0
    
    def test_format_text_response_without_suggestions(self, adapter, mock_turn_context):
        """Test text response formatting without suggestions."""
        text = "Simple text response"
        response_activity = adapter.format_text_response(mock_turn_context, text, include_suggestions=False)
        
        assert response_activity.text == text
        assert response_activity.suggested_actions is None
    
    def test_format_welcome_response(self, adapter, mock_turn_context):
        """Test welcome response formatting."""
        response_activity = adapter.format_welcome_response(mock_turn_context)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        
        # Check text contains bot name
        assert "Welcome to" in response_activity.text
        assert "Structural Engineering Assistant" in response_activity.text
    
    def test_format_help_response(self, adapter, mock_turn_context):
        """Test help response formatting."""
        response_activity = adapter.format_help_response(mock_turn_context)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        
        # Check text contains bot name
        assert "Here's how to use" in response_activity.text
        assert "Structural Engineering Assistant" in response_activity.text
    
    def test_format_error_response(self, adapter, mock_turn_context):
        """Test error response formatting."""
        error_message = "Test error message"
        response_activity = adapter.format_error_response(mock_turn_context, error_message)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        assert error_message in response_activity.text
    
    def test_format_loading_response(self, adapter, mock_turn_context):
        """Test loading response formatting."""
        response_activity = adapter.format_loading_response(mock_turn_context)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        assert "Processing your request" in response_activity.text
    
    def test_format_file_upload_response(self, adapter, mock_turn_context):
        """Test file upload response formatting."""
        file_name = "test.pdf"
        file_type = "application/pdf"
        response_activity = adapter.format_file_upload_response(mock_turn_context, file_name, file_type)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        assert file_name in response_activity.text
    
    def test_format_quick_actions_response(self, adapter, mock_turn_context):
        """Test quick actions response formatting."""
        response_activity = adapter.format_quick_actions_response(mock_turn_context)
        
        assert response_activity.attachments is not None
        assert len(response_activity.attachments) > 0
        assert response_activity.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
        assert "Choose a quick action" in response_activity.text
    
    def test_create_rag_response_card_with_sources(self, adapter, mock_rag_response):
        """Test RAG response card creation with sources."""
        card_json = adapter._create_rag_response_card(mock_rag_response)
        
        assert card_json["type"] == "AdaptiveCard"
        assert card_json["version"] == "1.4"
        assert len(card_json["body"]) > 0
        assert len(card_json["actions"]) > 0
        
        # Check sources section exists
        sources_section = next(
            (item for item in card_json["body"] if item.get("items", [{}])[0].get("text") == "📚 Sources"),
            None
        )
        assert sources_section is not None
    
    def test_create_rag_response_card_with_citations(self, adapter, mock_rag_response):
        """Test RAG response card creation with citations."""
        card_json = adapter._create_rag_response_card(mock_rag_response)
        
        # Check citations section exists
        citations_section = next(
            (item for item in card_json["body"] if item.get("items", [{}])[0].get("text") == "🔗 Citations"),
            None
        )
        assert citations_section is not None
    
    def test_create_rag_response_card_with_thoughts_disabled(self, adapter, mock_rag_response):
        """Test RAG response card creation with thoughts disabled."""
        adapter.config = TeamsCardConfig(show_thoughts=False)
        card_json = adapter._create_rag_response_card(mock_rag_response)
        
        # Check thoughts section does not exist
        thoughts_section = next(
            (item for item in card_json["body"] if item.get("items", [{}])[0].get("text") == "💭 Process"),
            None
        )
        assert thoughts_section is None
    
    def test_create_rag_response_card_with_usage_disabled(self, adapter, mock_rag_response):
        """Test RAG response card creation with usage disabled."""
        adapter.config = TeamsCardConfig(show_usage=False)
        card_json = adapter._create_rag_response_card(mock_rag_response)
        
        # Check usage section does not exist
        usage_section = next(
            (item for item in card_json["body"] if item.get("items", [{}])[0].get("text") == "📊 Usage"),
            None
        )
        assert usage_section is None
    
    def test_create_suggested_actions(self, adapter):
        """Test suggested actions creation."""
        suggested_actions = adapter._create_suggested_actions()
        
        assert len(suggested_actions) == len(TeamsTextConstants.SUGGESTED_ACTIONS)
        for i, action in enumerate(suggested_actions):
            assert action.title == TeamsTextConstants.SUGGESTED_ACTIONS[i]
    
    def test_error_handling_in_welcome_response(self, adapter, mock_turn_context):
        """Test error handling in welcome response."""
        with patch.object(adapter.teams_components, 'create_welcome_card', side_effect=Exception("Test error")):
            response_activity = adapter.format_welcome_response(mock_turn_context)
            
            assert response_activity.text is not None
            assert "Welcome to" in response_activity.text
    
    def test_error_handling_in_help_response(self, adapter, mock_turn_context):
        """Test error handling in help response."""
        with patch.object(adapter.teams_components, 'create_help_card', side_effect=Exception("Test error")):
            response_activity = adapter.format_help_response(mock_turn_context)
            
            assert response_activity.text is not None
            assert "Here's how to use" in response_activity.text