"""
Pytest tests for Teams handler functionality.
Tests Teams-specific message handling and adaptive card actions.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from botbuilder.schema import Activity, ActivityTypes

from handlers.teams_handler import TeamsHandler
from services.rag_service import RAGService, RAGRequest, RAGResponse
from services.auth_service import AuthService
from constants.teams_text import TeamsTextConstants


class MockTurnContext:
    """Mock TurnContext for testing."""
    
    def __init__(self, activity: Activity):
        self.activity = activity
        self.channel_id = "msteams"
        self.conversation = activity.conversation
        self.from_property = activity.from_property
        self.recipient = Mock()
        self.recipient.id = "bot1"


class TestTeamsHandler:
    """Test cases for TeamsHandler."""
    
    @pytest.fixture
    def mock_rag_service(self):
        """Create a mock RAG service."""
        return Mock(spec=RAGService)
    
    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        return Mock(spec=AuthService)
    
    @pytest.fixture
    def teams_handler(self, mock_rag_service, mock_auth_service):
        """Create a TeamsHandler instance for testing."""
        return TeamsHandler(mock_rag_service, mock_auth_service)
    
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
            answer="This is a test response.",
            sources=[{"title": "Source 1"}],
            citations=["Citation 1"],
            thoughts=[{"title": "Thought 1", "description": "Description 1"}],
            token_usage={"total_tokens": 100},
            model_info={"model": "gpt-4"}
        )
    
    @pytest.mark.asyncio
    async def test_handle_message_with_mention(self, teams_handler, mock_turn_context, mock_rag_response):
        """Test message handling with bot mention."""
        # Mock the mention detection
        with patch.object(teams_handler, '_is_bot_mentioned', return_value=True):
            with patch.object(teams_handler, '_remove_mention', return_value="What are the main benefits?"):
                with patch.object(teams_handler.rag_service, 'process_query', return_value=mock_rag_response):
                    with patch.object(teams_handler, '_create_adaptive_card_response', return_value=Mock()):
                        conversation_data = {"conversation_id": "conv1"}
                        user_data = {"conversation_history": []}
                        auth_claims = {"user_id": "user1"}
                        
                        response = await teams_handler.handle_message(
                            mock_turn_context, conversation_data, user_data, auth_claims
                        )
                        
                        assert response is not None
    
    @pytest.mark.asyncio
    async def test_handle_message_without_mention(self, teams_handler, mock_turn_context):
        """Test message handling without bot mention."""
        # Mock no mention
        with patch.object(teams_handler, '_is_bot_mentioned', return_value=False):
            with patch.object(teams_handler, '_create_mention_reminder', return_value=Mock()):
                conversation_data = {"conversation_id": "conv1"}
                user_data = {"conversation_history": []}
                auth_claims = {"user_id": "user1"}
                
                response = await teams_handler.handle_message(
                    mock_turn_context, conversation_data, user_data, auth_claims
                )
                
                assert response is not None
    
    @pytest.mark.asyncio
    async def test_handle_message_empty_text(self, teams_handler, mock_turn_context):
        """Test message handling with empty text."""
        mock_turn_context.activity.text = ""
        
        with patch.object(teams_handler, '_is_bot_mentioned', return_value=False):
            with patch.object(teams_handler, '_create_mention_reminder', return_value=Mock()):
                conversation_data = {"conversation_id": "conv1"}
                user_data = {"conversation_history": []}
                auth_claims = {"user_id": "user1"}
                
                response = await teams_handler.handle_message(
                    mock_turn_context, conversation_data, user_data, auth_claims
                )
                
                assert response is not None
    
    @pytest.mark.asyncio
    async def test_handle_adaptive_card_action_follow_up(self, teams_handler, mock_turn_context):
        """Test adaptive card action handling for follow-up."""
        mock_turn_context.activity.value = {"action": "follow_up"}
        
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_adaptive_card_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert TeamsTextConstants.FOLLOW_UP_RESPONSE in response.text
    
    @pytest.mark.asyncio
    async def test_handle_adaptive_card_action_search_related(self, teams_handler, mock_turn_context):
        """Test adaptive card action handling for search related."""
        mock_turn_context.activity.value = {"action": "search_related"}
        
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_adaptive_card_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert TeamsTextConstants.SEARCH_RELATED_RESPONSE in response.text
    
    @pytest.mark.asyncio
    async def test_handle_adaptive_card_action_summarize(self, teams_handler, mock_turn_context):
        """Test adaptive card action handling for summarize."""
        mock_turn_context.activity.value = {"action": "summarize"}
        
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_adaptive_card_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert TeamsTextConstants.SUMMARIZE_RESPONSE in response.text
    
    @pytest.mark.asyncio
    async def test_handle_adaptive_card_action_unknown(self, teams_handler, mock_turn_context):
        """Test adaptive card action handling for unknown action."""
        mock_turn_context.activity.value = {"action": "unknown_action"}
        
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_adaptive_card_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert "unknown_action" in response.text
    
    @pytest.mark.asyncio
    async def test_handle_follow_up_action(self, teams_handler, mock_turn_context):
        """Test follow-up action handling."""
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_follow_up_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert TeamsTextConstants.FOLLOW_UP_RESPONSE in response.text
    
    @pytest.mark.asyncio
    async def test_handle_search_related_action(self, teams_handler, mock_turn_context):
        """Test search related action handling."""
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_search_related_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert TeamsTextConstants.SEARCH_RELATED_RESPONSE in response.text
    
    @pytest.mark.asyncio
    async def test_handle_summarize_action(self, teams_handler, mock_turn_context):
        """Test summarize action handling."""
        conversation_data = {"conversation_id": "conv1"}
        user_data = {"conversation_history": []}
        auth_claims = {"user_id": "user1"}
        
        response = await teams_handler._handle_summarize_action(
            mock_turn_context, conversation_data, user_data, auth_claims
        )
        
        assert response is not None
        assert TeamsTextConstants.SUMMARIZE_RESPONSE in response.text
    
    @pytest.mark.asyncio
    async def test_is_bot_mentioned_true(self, teams_handler, mock_turn_context):
        """Test bot mention detection when mentioned."""
        # Mock activity with mention
        mock_turn_context.activity.entities = [
            Mock(type="mention", as_dict=lambda: {"mentioned": {"id": "bot1"}})
        ]
        
        result = await teams_handler._is_bot_mentioned(mock_turn_context)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_bot_mentioned_false(self, teams_handler, mock_turn_context):
        """Test bot mention detection when not mentioned."""
        # Mock activity without mention
        mock_turn_context.activity.entities = []
        
        result = await teams_handler._is_bot_mentioned(mock_turn_context)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_remove_mention(self, teams_handler, mock_turn_context):
        """Test mention removal from message text."""
        # Mock activity with Teams-style mention tags
        mock_turn_context.activity.text = "<at>RAG Assistant</at> What are the main benefits?"
        
        result = await teams_handler._remove_mention(mock_turn_context)
        assert result == "What are the main benefits?"
    
    @pytest.mark.asyncio
    async def test_create_mention_reminder(self, teams_handler, mock_turn_context):
        """Test mention reminder creation."""
        response = await teams_handler._create_mention_reminder(mock_turn_context)
        
        assert response is not None
        assert TeamsTextConstants.format_mention_reminder() in response.text
    
    @pytest.mark.asyncio
    async def test_handle_file_upload(self, teams_handler, mock_turn_context):
        """Test file upload handling."""
        # Mock file attachment
        mock_turn_context.activity.attachments = [
            Mock(content_type="application/vnd.microsoft.teams.file.download.info")
        ]
        
        conversation_data = {"conversation_id": "conv1"}
        
        response = await teams_handler.handle_file_upload(
            mock_turn_context, conversation_data
        )
        
        assert response is not None
        assert "file" in response.text.lower()
    
    # Note: handle_members_added and handle_members_removed methods don't exist in TeamsHandler
    
    @pytest.mark.asyncio
    async def test_create_adaptive_card_response(self, teams_handler, mock_turn_context, mock_rag_response):
        """Test adaptive card response creation."""
        conversation_data = Mock()
        conversation_data.conversation_id = "conv1"
        
        response = await teams_handler._create_adaptive_card_response(
            mock_turn_context, mock_rag_response, conversation_data
        )
        
        assert response is not None
        assert response.attachments is not None
        assert len(response.attachments) > 0
        assert response.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_message_handling(self, teams_handler, mock_turn_context):
        """Test error handling in message handling."""
        with patch.object(teams_handler, '_is_bot_mentioned', side_effect=Exception("Test error")):
            conversation_data = {"conversation_id": "conv1"}
            user_data = {"conversation_history": []}
            auth_claims = {"user_id": "user1"}
            
            response = await teams_handler.handle_message(
                mock_turn_context, conversation_data, user_data, auth_claims
            )
            
            assert response is not None
            assert "error" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_adaptive_card_action(self, teams_handler, mock_turn_context):
        """Test error handling in adaptive card action handling."""
        mock_turn_context.activity.value = {"action": "follow_up"}
        
        with patch.object(teams_handler, '_handle_follow_up_action', side_effect=Exception("Test error")):
            conversation_data = {"conversation_id": "conv1"}
            user_data = {"conversation_history": []}
            auth_claims = {"user_id": "user1"}
            
            response = await teams_handler._handle_adaptive_card_action(
                mock_turn_context, conversation_data, user_data, auth_claims
            )
            
            assert response is not None
            assert "error" in response.text.lower()