"""
This module contains classes for loading configurations and creating Azure OpenAI models.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "app/backend"))

import os
from dataclasses import dataclass
from typing import Tuple

from config import CONFIG_OPENAI_CLIENT, CONFIG_AUTH_CLIENT


@dataclass
class AzureConfig:
    """Configuration for Azure OpenAI services."""
    api_version: str
    deployment_name: str
    endpoint: str
    api_key: str


@dataclass
class EmbeddingConfig(AzureConfig):
    """Configuration specific to Azure OpenAI embeddings."""
    model_name: str

class ConfigLoader:
    """Handles environment configuration loading."""
    
    @staticmethod
    def load_llm_config() -> Tuple[AzureConfig]:
        """Load configurations from environment variables."""
        
        llm_config = AzureConfig(
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"]
        )
        return llm_config    
    
    @staticmethod
    def load_embed_config() -> Tuple[EmbeddingConfig]:
        """Load configurations from environment variables."""

        embed_config = EmbeddingConfig(
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            deployment_name="",  # Not needed for embeddings
            endpoint=os.environ["AZURE_OPENAI_EMBEDDINGS_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_EMBEDDINGS_API_KEY"],
            model_name=os.environ["AZURE_OPENAI_EMBEDDINGS_MODEL"]
        )
        return embed_config
    

class ModelFactory:
    """Factory for creating Azure OpenAI models."""
    
    @staticmethod
    def create_embedder(config: EmbeddingConfig):
        """Create an embedding model instance."""
        from llm_wrapper import AzureOpenAIEmbeddingModel
        
        return AzureOpenAIEmbeddingModel(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
            model_name=config.model_name
        )
    
    @staticmethod
    def create_llm_model(config: AzureConfig):
        """Create llm model instance."""
        from llm_wrapper import AzureOpenAI
        
        return AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,    
            deployment_name=config.deployment_name
        )
    
    @staticmethod
    def from_app_config(current_app):
        """Create models from Quart app config."""
        from llm_wrapper import AzureOpenAIEmbeddingModel, AzureOpenAI
        openai_client = current_app.config[CONFIG_OPENAI_CLIENT]
        auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
        
        model_name = os.getenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4")
        deployment_name = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        llm = AzureOpenAI(
            client_auth=(openai_client, auth_helper),
            model_name=model_name,
            deployment_name=deployment_name
        )
        
        embedding_model = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002")
        embedding_deployment = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
        embedder = AzureOpenAIEmbeddingModel(
            client_auth=(openai_client, auth_helper),
            model_name=embedding_model,
            deployment_name=embedding_deployment
        )

        return llm, embedder