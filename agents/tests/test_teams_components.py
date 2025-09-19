"""
Pytest tests for Teams components functionality.
Tests Teams-specific UI components and utilities.
"""

import pytest
from unittest.mock import Mock, patch
from botbuilder.schema import Activity, ActivityTypes

from components.teams_components import TeamsComponents, TeamsCardConfig
from constants.teams_text import TeamsTextConstants


class TestTeamsComponents:
    """Test cases for TeamsComponents."""
    
    def test_create_welcome_card(self):
        """Test welcome card creation."""
        card = TeamsComponents.create_welcome_card()
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0
        
        # Check title contains bot name
        title_text = card["body"][0]["items"][0]["text"]
        assert "Welcome to" in title_text
        assert "Structural Engineering Assistant" in title_text
        
        # Check capabilities section exists
        capabilities_section = next(
            (item for item in card["body"] if item.get("items", [{}])[0].get("text") == "🔧 What I can do:"),
            None
        )
        assert capabilities_section is not None
        
        # Check usage section exists
        usage_section = next(
            (item for item in card["body"] if item.get("items", [{}])[0].get("text") == "💡 How to use:"),
            None
        )
        assert usage_section is not None
    
    def test_create_help_card(self):
        """Test help card creation."""
        card = TeamsComponents.create_help_card()
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0
        
        # Check title contains bot name
        title_text = card["body"][0]["items"][0]["text"]
        assert "Help" in title_text
        assert "Structural Engineering Assistant" in title_text
        
        # Check structural analysis section
        analysis_section = next(
            (item for item in card["body"] if item.get("items", [{}])[0].get("text") == "📐 Structural Analysis"),
            None
        )
        assert analysis_section is not None
        
        # Check technical chat section
        chat_section = next(
            (item for item in card["body"] if item.get("items", [{}])[0].get("text") == "💬 Technical Chat"),
            None
        )
        assert chat_section is not None
        
        # Check example questions section
        examples_section = next(
            (item for item in card["body"] if item.get("items", [{}])[0].get("text") == "🔍 Example Questions"),
            None
        )
        assert examples_section is not None
    
    def test_create_error_card(self):
        """Test error card creation."""
        error_message = "Test error message"
        card = TeamsComponents.create_error_card(error_message)
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0
        
        # Check error message is included
        error_text = card["body"][1]["text"]
        assert error_message in error_text
        
        # Check error title
        error_title = card["body"][0]["items"][0]["text"]
        assert "Error" in error_title
    
    def test_create_loading_card(self):
        """Test loading card creation."""
        card = TeamsComponents.create_loading_card()
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        
        # Check loading message
        loading_text = card["body"][0]["items"][0]["text"]
        assert "Processing your request" in loading_text
    
    def test_create_file_upload_card(self):
        """Test file upload card creation."""
        file_name = "test.pdf"
        file_type = "application/pdf"
        card = TeamsComponents.create_file_upload_card(file_name, file_type)
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0
        
        # Check file name is included
        file_text = card["body"][1]["text"]
        assert file_name in file_text
        
        # Check file type is included
        type_text = card["body"][2]["text"]
        assert file_type in type_text
    
    def test_create_quick_actions_card(self):
        """Test quick actions card creation."""
        card = TeamsComponents.create_quick_actions_card()
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0
        
        # Check quick actions title
        title_text = card["body"][0]["items"][0]["text"]
        assert "Quick Actions" in title_text
    
    def test_create_attachment_from_card(self):
        """Test attachment creation from card JSON."""
        card_json = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [{"type": "TextBlock", "text": "Test"}]
        }
        
        attachment = TeamsComponents.create_attachment_from_card(card_json)
        
        assert attachment.content_type == "application/vnd.microsoft.card.adaptive"
        assert attachment.content == card_json
    
    def test_create_suggested_actions(self):
        """Test suggested actions creation."""
        actions = ["Action 1", "Action 2", "Action 3"]
        suggested_actions = TeamsComponents.create_suggested_actions(actions)
        
        assert len(suggested_actions) == 3
        for i, action in enumerate(suggested_actions):
            assert action.title == actions[i]
            assert action.value == actions[i]
    
    def test_get_default_suggested_actions(self):
        """Test default suggested actions."""
        suggested_actions = TeamsComponents.get_default_suggested_actions()
        
        assert len(suggested_actions) == len(TeamsTextConstants.SUGGESTED_ACTIONS)
        for i, action in enumerate(suggested_actions):
            assert action.title == TeamsTextConstants.SUGGESTED_ACTIONS[i]


class TestTeamsCardConfig:
    """Test cases for TeamsCardConfig."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = TeamsCardConfig()
        
        assert config.show_sources == True
        assert config.show_citations == True
        assert config.show_thoughts == False
        assert config.show_usage == False
        assert config.max_sources == 3
        assert config.max_citations == 3
        assert config.max_thoughts == 2
        assert config.include_actions == True
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = TeamsCardConfig(
            show_sources=False,
            show_citations=True,
            show_thoughts=True,
            show_usage=True,
            max_sources=5,
            max_citations=2,
            max_thoughts=1,
            include_actions=False
        )
        
        assert config.show_sources == False
        assert config.show_citations == True
        assert config.show_thoughts == True
        assert config.show_usage == True
        assert config.max_sources == 5
        assert config.max_citations == 2
        assert config.max_thoughts == 1
        assert config.include_actions == False


class TestTeamsTextConstants:
    """Test cases for TeamsTextConstants."""
    
    def test_get_bot_name(self):
        """Test bot name retrieval."""
        with patch.dict('os.environ', {'AGENT_NAME': 'Test Bot'}):
            assert TeamsTextConstants.get_bot_name() == 'Test Bot'
        
        with patch.dict('os.environ', {}, clear=True):
            assert TeamsTextConstants.get_bot_name() == TeamsTextConstants.DEFAULT_BOT_NAME
    
    def test_get_bot_description(self):
        """Test bot description retrieval."""
        with patch.dict('os.environ', {'AGENT_DESCRIPTION': 'Test Description'}):
            assert TeamsTextConstants.get_bot_description() == 'Test Description'
        
        with patch.dict('os.environ', {}, clear=True):
            assert TeamsTextConstants.get_bot_description() == TeamsTextConstants.DEFAULT_BOT_DESCRIPTION
    
    def test_format_welcome_title(self):
        """Test welcome title formatting."""
        with patch.dict('os.environ', {'AGENT_NAME': 'Test Bot'}):
            title = TeamsTextConstants.format_welcome_title()
            assert 'Welcome to Test Bot' in title
            assert '🏗️' in title
    
    def test_format_welcome_description(self):
        """Test welcome description formatting."""
        with patch.dict('os.environ', {'AGENT_DESCRIPTION': 'Test Description'}):
            description = TeamsTextConstants.format_welcome_description()
            assert 'Test Description' in description
    
    def test_format_help_title(self):
        """Test help title formatting."""
        with patch.dict('os.environ', {'AGENT_NAME': 'Test Bot'}):
            title = TeamsTextConstants.format_help_title()
            assert 'Test Bot Help' in title
            assert '❓' in title
    
    def test_format_usage_instructions(self):
        """Test usage instructions formatting."""
        with patch.dict('os.environ', {'AGENT_NAME': 'Test Bot'}):
            instructions = TeamsTextConstants.format_usage_instructions()
            assert len(instructions) == len(TeamsTextConstants.USAGE_INSTRUCTIONS)
            # Only the first instruction should contain the bot name
            assert 'Test Bot' in instructions[0]
    
    def test_format_mention_reminder(self):
        """Test mention reminder formatting."""
        with patch.dict('os.environ', {'AGENT_NAME': 'Test Bot'}):
            reminder = TeamsTextConstants.format_mention_reminder()
            assert 'Test Bot' in reminder
            assert '👋' in reminder
    
    def test_format_file_upload_message(self):
        """Test file upload message formatting."""
        message = TeamsTextConstants.format_file_upload_message("test.pdf")
        assert "test.pdf" in message
        assert "**test.pdf**" in message
    
    def test_format_file_upload_type(self):
        """Test file upload type formatting."""
        file_type = TeamsTextConstants.format_file_upload_type("application/pdf")
        assert "application/pdf" in file_type
        assert "File type:" in file_type