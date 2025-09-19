"""
Constants for Teams UI text content.
This module contains all text strings used in Teams UI components and responses.
"""

import os
from typing import Dict, List


class TeamsTextConstants:
    """Constants for Teams UI text content."""
    
    # Bot configuration
    DEFAULT_BOT_NAME = "Structural Engineering Assistant"
    DEFAULT_BOT_DESCRIPTION = "AI-powered structural engineering document search and analysis assistant"
    
    # Welcome messages
    WELCOME_TITLE = "🏗️ Welcome to {bot_name}"
    WELCOME_DESCRIPTION = "{bot_description}. I can help you analyze structural engineering documents, answer technical questions, and provide insights from your project files."
    WELCOME_FALLBACK = "Welcome to {bot_name}! {bot_description}. I can help you analyze structural engineering documents, answer technical questions, and provide insights from your project files."
    
    # Help messages
    HELP_TITLE = "❓ {bot_name} Help"
    HELP_MAIN_TEXT = "Here's how to use {bot_name}:"
    HELP_FALLBACK = "Here's how to use {bot_name}:\n\n• Mention me with @{bot_name}\n• Upload structural drawings, specs, or reports\n• Ask technical questions about your projects\n• Use the buttons in my responses for quick actions"
    
    # Capabilities
    CAPABILITIES_TITLE = "🔧 What I can do:"
    CAPABILITIES = [
        "• Analyze structural drawings and specifications",
        "• Answer questions about building codes and standards", 
        "• Review calculations and design reports",
        "• Provide technical insights and recommendations",
        "• Help with material specifications and load calculations"
    ]
    
    # Usage instructions
    USAGE_TITLE = "💡 How to use:"
    USAGE_INSTRUCTIONS = [
        "• Mention me with @{bot_name}",
        "• Upload structural drawings, specs, or reports",
        "• Ask technical questions about your projects"
    ]
    
    # Help sections
    STRUCTURAL_ANALYSIS_TITLE = "📐 Structural Analysis"
    STRUCTURAL_ANALYSIS_ITEMS = [
        "• Analyze structural drawings and specifications",
        "• Review load calculations and design reports",
        "• Check compliance with building codes"
    ]
    
    TECHNICAL_CHAT_TITLE = "💬 Technical Chat"
    TECHNICAL_CHAT_ITEMS = [
        "• Ask questions about structural engineering concepts",
        "• Get explanations of design principles",
        "• Request material and code recommendations"
    ]
    
    EXAMPLE_QUESTIONS_TITLE = "🔍 Example Questions"
    EXAMPLE_QUESTIONS = [
        "• 'What are the load requirements for this beam design?'",
        "• 'Can you review this foundation calculation?'",
        "• 'What building code applies to this steel structure?'"
    ]
    
    # Suggested actions
    SUGGESTED_ACTIONS = [
        "🔍 Analyze Drawing",
        "📐 Review Calculation", 
        "❓ Ask Technical Question",
        "📋 Upload Specification",
        "❓ Help"
    ]
    
    # Action button labels
    ACTION_GET_STARTED = "🚀 Get Started"
    ACTION_HELP = "❓ Help"
    ACTION_TRY_NOW = "🚀 Try It Now"
    ACTION_UPLOAD_DRAWING = "📐 Upload Drawing"
    ACTION_ASK_FOLLOW_UP = "💬 Ask Follow-up"
    ACTION_SEARCH_RELATED = "🔍 Search Related"
    ACTION_SUMMARIZE = "📋 Summarize"
    
    # Error messages
    ERROR_PROCESSING_REQUEST = "I'm sorry, I encountered an error processing your request. Please try again."
    ERROR_ADAPTIVE_CARD_ACTION = "I encountered an error processing your action. Please try asking me a question directly."
    ERROR_WELCOME_FORMATTING = "Error formatting welcome response"
    ERROR_HELP_FORMATTING = "Error formatting help response"
    
    # Follow-up action responses
    FOLLOW_UP_RESPONSE = """I'd be happy to provide more details! What specific aspect would you like me to elaborate on? You can ask me to:

• Explain any part in more detail
• Provide examples
• Compare different options
• Answer related questions

Just type your question and I'll help you out!"""
    
    SEARCH_RELATED_RESPONSE = """I can help you find more information about this topic! Try asking me:

• 'What are the requirements for...?'
• 'How do I apply for...?'
• 'What are the steps to...?'
• 'Tell me more about...'

Or just describe what you're looking for and I'll search through the documents for you!"""
    
    SUMMARIZE_RESPONSE = """I can help you summarize information! You can ask me to:

• 'Summarize the key points'
• 'Give me a brief overview'
• 'What are the main takeaways?'
• 'Create a bullet point summary'

Just let me know what you'd like me to summarize!"""
    
    # File upload messages
    FILE_UPLOAD_TITLE = "📎 File Uploaded"
    FILE_UPLOAD_MESSAGE = "I've received your file: **{file_name}**"
    FILE_UPLOAD_TYPE = "File type: {file_type}"
    FILE_UPLOAD_HELP = "I can help you search through this document and answer questions about its content. What would you like to know?"
    
    # Loading messages
    LOADING_TITLE = "🔄 Processing your request..."
    LOADING_MESSAGE = "Please wait while I search through your documents and generate a response."
    
    # Quick actions
    QUICK_ACTIONS_TITLE = "⚡ Quick Actions"
    QUICK_ACTIONS_MESSAGE = "Choose a quick action to get started:"
    
    # Mention reminder
    MENTION_REMINDER = """👋 Hi! I'm your AI assistant. To ask me a question, please mention me using @{bot_name} or type your question directly."""
    
    @classmethod
    def get_bot_name(cls) -> str:
        """Get bot name from environment or default."""
        return os.getenv("AGENT_NAME", cls.DEFAULT_BOT_NAME)
    
    @classmethod
    def get_bot_description(cls) -> str:
        """Get bot description from environment or default."""
        return os.getenv("AGENT_DESCRIPTION", cls.DEFAULT_BOT_DESCRIPTION)
    
    @classmethod
    def format_welcome_title(cls) -> str:
        """Format welcome title with bot name."""
        return cls.WELCOME_TITLE.format(bot_name=cls.get_bot_name())
    
    @classmethod
    def format_welcome_description(cls) -> str:
        """Format welcome description with bot description."""
        return cls.WELCOME_DESCRIPTION.format(bot_description=cls.get_bot_description())
    
    @classmethod
    def format_welcome_fallback(cls) -> str:
        """Format welcome fallback message."""
        return cls.WELCOME_FALLBACK.format(
            bot_name=cls.get_bot_name(),
            bot_description=cls.get_bot_description()
        )
    
    @classmethod
    def format_help_title(cls) -> str:
        """Format help title with bot name."""
        return cls.HELP_TITLE.format(bot_name=cls.get_bot_name())
    
    @classmethod
    def format_help_main_text(cls) -> str:
        """Format help main text with bot name."""
        return cls.HELP_MAIN_TEXT.format(bot_name=cls.get_bot_name())
    
    @classmethod
    def format_help_fallback(cls) -> str:
        """Format help fallback message."""
        return cls.HELP_FALLBACK.format(bot_name=cls.get_bot_name())
    
    @classmethod
    def format_usage_instructions(cls) -> List[str]:
        """Format usage instructions with bot name."""
        return [instruction.format(bot_name=cls.get_bot_name()) for instruction in cls.USAGE_INSTRUCTIONS]
    
    @classmethod
    def format_mention_reminder(cls) -> str:
        """Format mention reminder with bot name."""
        return cls.MENTION_REMINDER.format(bot_name=cls.get_bot_name())
    
    @classmethod
    def format_file_upload_message(cls, file_name: str) -> str:
        """Format file upload message with file name."""
        return cls.FILE_UPLOAD_MESSAGE.format(file_name=file_name)
    
    @classmethod
    def format_file_upload_type(cls, file_type: str) -> str:
        """Format file upload type with file type."""
        return cls.FILE_UPLOAD_TYPE.format(file_type=file_type)