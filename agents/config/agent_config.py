"""
Configuration for Microsoft 365 Agents SDK integration.
This module handles configuration for the agent application.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the Microsoft 365 Agent."""
    
    # Bot Framework Configuration
    app_id: str
    app_password: str
    
    # Microsoft 365 Configuration
    tenant_id: str
    client_id: str
    client_secret: str
    
    # Backend API Configuration
    backend_url: str
    
    # Azure Services (reuse from existing app)
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    azure_search_endpoint: str
    azure_search_key: str
    azure_search_index: str
    
    # Agent Settings
    agent_name: str = "RAG Assistant"
    agent_description: str = "AI-powered document search and chat assistant"
    max_conversation_turns: int = 20
    enable_typing_indicator: bool = True
    
    # Channel Settings
    enable_teams: bool = True
    enable_copilot: bool = True
    enable_web_chat: bool = True
    
    @classmethod
    def from_environment(cls) -> "AgentConfig":
        """Create configuration from environment variables."""
        return cls(
            # Bot Framework
            app_id=os.getenv("MICROSOFT_APP_ID", ""),
            app_password=os.getenv("MICROSOFT_APP_PASSWORD", ""),
            
            # Microsoft 365
            tenant_id=os.getenv("AZURE_TENANT_ID", ""),
            client_id=os.getenv("AZURE_CLIENT_ID", ""),
            client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
            
            # Backend API
            backend_url=os.getenv("BACKEND_URL", "http://localhost:50505"),
            
            # Azure Services
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", ""),
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            azure_search_key=os.getenv("AZURE_SEARCH_KEY", ""),
            azure_search_index=os.getenv("AZURE_SEARCH_INDEX", ""),
            
            # Agent Settings
            agent_name=os.getenv("AGENT_NAME", "RAG Assistant"),
            agent_description=os.getenv("AGENT_DESCRIPTION", "AI-powered document search and chat assistant"),
            max_conversation_turns=int(os.getenv("MAX_CONVERSATION_TURNS", "20")),
            enable_typing_indicator=os.getenv("ENABLE_TYPING_INDICATOR", "true").lower() == "true",
            
            # Channel Settings
            enable_teams=os.getenv("ENABLE_TEAMS", "true").lower() == "true",
            enable_copilot=os.getenv("ENABLE_COPILOT", "true").lower() == "true",
            enable_web_chat=os.getenv("ENABLE_WEB_CHAT", "true").lower() == "true",
        )
    
    def validate(self) -> None:
        """Validate configuration."""
        # For production: require all fields
        # For emulator/testing: app_id/app_password can be empty (adapter will skip auth)
        required_fields = [
            "tenant_id", "client_id", "client_secret", "backend_url"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
        
        # Warn if app_id/password missing (needed for production, optional for emulator)
        if not self.app_id or not self.app_password:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("MICROSOFT_APP_ID or MICROSOFT_APP_PASSWORD not set - emulator/testing mode (auth will be skipped)")
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")