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
    azure_token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    return openai.AzureOpenAI(
        api_version="2024-02-15-preview",
        azure_endpoint=oai_config["azure_endpoint"],
        azure_ad_token_provider=azure_token_provider,
        azure_deployment=oai_config["azure_deployment"],
    )
