import logging
import os

import openai
from azure.ai.evaluation import AzureOpenAIModelConfiguration, OpenAIModelConfiguration
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient

logger = logging.getLogger("evaltools")


def get_azd_credential(tenant_id: str | None) -> AzureDeveloperCliCredential:
    if tenant_id:
        logger.info("Using Azure Developer CLI Credential for tenant %s", tenant_id)
        return AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    logger.info("Using Azure Developer CLI Credential for home tenant")
    return AzureDeveloperCliCredential(process_timeout=60)


def get_openai_config() -> dict:
    if os.environ.get("OPENAI_HOST") == "azure":
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_deployment = os.environ.get("AZURE_OPENAI_EVAL_DEPLOYMENT")
        if os.environ.get("AZURE_OPENAI_KEY"):
            logger.info("Using Azure OpenAI Service with API Key from AZURE_OPENAI_KEY")
            openai_config: AzureOpenAIModelConfiguration = {
                "azure_endpoint": azure_endpoint,
                "api_key": os.environ["AZURE_OPENAI_KEY"],
                "azure_deployment": azure_deployment,
            }
        else:
            logger.info("Using Azure OpenAI Service with Azure Developer CLI Credential")
            openai_config: AzureOpenAIModelConfiguration = {
                "azure_endpoint": azure_endpoint,
                "azure_deployment": azure_deployment,
            }
            # azure-ai-evaluate will call DefaultAzureCredential behind the scenes,
            # so we must be logged in to Azure CLI with the correct tenant
    else:
        logger.info("Using OpenAI Service with API Key from OPENAICOM_KEY")
        openai_config: OpenAIModelConfiguration = {
            "api_key": os.environ["OPENAICOM_KEY"],
            "organization": os.environ["OPENAICOM_ORGANIZATION"],
            "model": os.environ["OPENAI_GPT_MODEL"],
        }
    return openai_config


def get_openai_config_dict() -> dict:
    """Return a dictionary with OpenAI configuration based on environment variables.
    This is only used by azure-ai-generative SDK right now, and should be deprecated once
    the generate functionality is available in azure-ai-evaluation SDK.
    """
    if os.environ.get("OPENAI_HOST") == "azure":
        if os.environ.get("AZURE_OPENAI_KEY"):
            logger.info("Using Azure OpenAI Service with API Key from AZURE_OPENAI_KEY")
            api_key = os.environ["AZURE_OPENAI_KEY"]
        else:
            logger.info("Using Azure OpenAI Service with Azure Developer CLI Credential")
            azure_credential = get_azd_credential(os.environ.get("AZURE_OPENAI_TENANT_ID"))
            api_key = azure_credential.get_token("https://cognitiveservices.azure.com/.default").token
        openai_config = {
            "api_type": "azure",
            "api_base": os.environ["AZURE_OPENAI_ENDPOINT"],
            "api_key": api_key,
            "api_version": "2024-02-15-preview",
            "deployment": os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"],
            "model": os.environ["OPENAI_GPT_MODEL"],
        }
    else:
        logger.info("Using OpenAI Service with API Key from OPENAICOM_KEY")
        openai_config = {
            "api_type": "openai",
            "api_key": os.environ["OPENAICOM_KEY"],
            "organization": os.environ["OPENAICOM_ORGANIZATION"],
            "model": os.environ["OPENAI_GPT_MODEL"],
            "deployment": "none-needed-for-openaicom",
        }
    return openai_config


def get_search_client():
    if api_key := os.environ.get("AZURE_SEARCH_KEY"):
        logger.info("Using Azure Search Service with API Key from AZURE_SEARCH_KEY")
        azure_credential = AzureKeyCredential(api_key)
    else:
        logger.info("Using Azure Search Service with Azure Developer CLI Credential")
        azure_credential = get_azd_credential(os.environ.get("AZURE_SEARCH_TENANT_ID"))

    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=os.environ["AZURE_SEARCH_INDEX"],
        credential=azure_credential,
    )


def get_openai_client(oai_config: AzureOpenAIModelConfiguration | OpenAIModelConfiguration, azure_credential=None):
    if "azure_deployment" in oai_config:
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
            azure_endpoint=oai_config["azure_endpoint"],
            api_key=oai_config["api_key"] if oai_config.get("api_key") else None,
            azure_ad_token_provider=azure_token_provider,
            azure_deployment=oai_config["azure_deployment"],
        )
    elif "organization" in oai_config:
        oai_config: OpenAIModelConfiguration = oai_config
        return openai.OpenAI(api_key=oai_config["api_key"], organization=oai_config["organization"])
