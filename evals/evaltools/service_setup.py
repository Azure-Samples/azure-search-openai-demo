import logging
import os
from typing import cast

import openai
from azure.ai.evaluation import AzureOpenAIModelConfiguration, OpenAIModelConfiguration
from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider

logger = logging.getLogger("evaltools")


def get_azd_credential(tenant_id: str | None) -> AzureDeveloperCliCredential:
    if tenant_id:
        logger.info("Using Azure Developer CLI Credential for tenant %s", tenant_id)
        return AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    logger.info("Using Azure Developer CLI Credential for home tenant")
    return AzureDeveloperCliCredential(process_timeout=60)


def get_openai_config() -> AzureOpenAIModelConfiguration | OpenAIModelConfiguration:
    if os.environ.get("OPENAI_HOST") == "azure":
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        azure_deployment = os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"]
        azure_config: AzureOpenAIModelConfiguration
        if os.environ.get("AZURE_OPENAI_KEY"):
            logger.info("Using Azure OpenAI Service with API Key from AZURE_OPENAI_KEY")
            azure_config = {
                "azure_endpoint": azure_endpoint,
                "api_key": os.environ["AZURE_OPENAI_KEY"],
                "azure_deployment": azure_deployment,
            }
        else:
            logger.info("Using Azure OpenAI Service with Azure Developer CLI Credential")
            azure_config = {
                "azure_endpoint": azure_endpoint,
                "azure_deployment": azure_deployment,
            }
            # azure-ai-evaluate will call DefaultAzureCredential behind the scenes,
            # so we must be logged in to Azure CLI with the correct tenant
        return azure_config
    else:
        logger.info("Using OpenAI Service with API Key from OPENAICOM_KEY")
        openai_config: OpenAIModelConfiguration = {
            "api_key": os.environ["OPENAICOM_KEY"],
            "organization": os.environ["OPENAICOM_ORGANIZATION"],
            "model": os.environ["OPENAI_GPT_MODEL"],
        }
        return openai_config


def get_openai_client(oai_config: AzureOpenAIModelConfiguration | OpenAIModelConfiguration, azure_credential=None):
    if "azure_deployment" in oai_config:
        azure_config = cast(AzureOpenAIModelConfiguration, oai_config)
        azure_token_provider = None

        if azure_credential is None and not os.environ.get("AZURE_OPENAI_KEY"):
            logger.info("Using Azure OpenAI Service with Azure Developer CLI Credential")
            azure_credential = get_azd_credential(os.environ.get("AZURE_OPENAI_TENANT_ID"))
        if azure_credential is not None:
            azure_token_provider = get_bearer_token_provider(
                azure_credential, "https://cognitiveservices.azure.com/.default"
            )
        return openai.AzureOpenAI(
            api_version="2024-02-15-preview",
            azure_endpoint=azure_config["azure_endpoint"],
            api_key=azure_config["api_key"] if azure_config.get("api_key") else None,
            azure_ad_token_provider=azure_token_provider,
            azure_deployment=azure_config["azure_deployment"],
        )
    elif "organization" in oai_config:
        openai_config = cast(OpenAIModelConfiguration, oai_config)
        return openai.OpenAI(api_key=openai_config["api_key"], organization=openai_config["organization"])
