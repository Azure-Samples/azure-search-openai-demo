import logging
import os

import openai
from azure.ai.evaluation import AzureOpenAIModelConfiguration
from azure.identity import get_bearer_token_provider

logger = logging.getLogger("evaltools")


def get_openai_config() -> AzureOpenAIModelConfiguration:
    logger.info("Using Azure OpenAI Service with keyless authentication")
    # azure-ai-evaluation will call DefaultAzureCredential behind the scenes,
    # so we must be logged in to Azure CLI with the correct tenant.
    azure_config: AzureOpenAIModelConfiguration = {
        "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
        "azure_deployment": os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"],
    }
    return azure_config


def get_openai_client(oai_config: AzureOpenAIModelConfiguration, azure_credential):
    # Use the OpenAI v1 API surface (base_url ending in /openai/v1) with a bearer token
    # provider passed as api_key, matching the app backend. This uses the Responses API
    # and does not require pinning an Azure OpenAI api_version.
    azure_token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    return openai.OpenAI(
        base_url=f"{oai_config['azure_endpoint'].rstrip('/')}/openai/v1",
        api_key=azure_token_provider,
    )
