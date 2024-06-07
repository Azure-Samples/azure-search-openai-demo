import logging
import os

import openai
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from promptflow.core import AzureOpenAIModelConfiguration, ModelConfiguration, OpenAIModelConfiguration

logger = logging.getLogger("scripts")


def get_openai_config() -> ModelConfiguration:
    if os.environ.get("OPENAI_HOST") == "azure":
        azure_endpoint = f"https://{os.environ['AZURE_OPENAI_SERVICE']}.openai.azure.com"
        azure_deployment = os.environ.get("AZURE_OPENAI_EVAL_DEPLOYMENT")
        api_version = "2023-07-01-preview"
        if os.environ.get("AZURE_OPENAI_KEY"):
            logger.info("Using Azure OpenAI Service with API Key from AZURE_OPENAI_KEY")
            openai_config = AzureOpenAIModelConfiguration(
                azure_endpoint=azure_endpoint,
                azure_deployment=azure_deployment,
                api_version=api_version,
                api_key=os.environ["AZURE_OPENAI_KEY"],
            )
        else:
            logger.info("Using Azure OpenAI Service with Azure Developer CLI Credential")
            openai_config = AzureOpenAIModelConfiguration(
                azure_endpoint=azure_endpoint, azure_deployment=azure_deployment, api_version=api_version
            )
            # PromptFlow will call DefaultAzureCredential behind the scenes
        openai_config.model = os.environ["OPENAI_GPT_MODEL"]
    else:
        logger.info("Using OpenAI Service with API Key from OPENAICOM_KEY")
        openai_config = OpenAIModelConfiguration(
            model=os.environ["OPENAI_GPT_MODEL"],
            api_key=os.environ.get("AZURE_OPENAI_KEY"),
            organization=os.environ["OPENAICOM_ORGANIZATION"],
        )
    return openai_config


def get_openai_config_dict() -> dict:
    """Return a dictionary with OpenAI configuration based on environment variables.
    This is only used by azure-ai-generative SDK right now, and should be deprecated once
    the generate functionality is available in promptflow SDK.
    """
    if os.environ.get("OPENAI_HOST") == "azure":
        if os.environ.get("AZURE_OPENAI_KEY"):
            logger.info("Using Azure OpenAI Service with API Key from AZURE_OPENAI_KEY")
            api_key = os.environ["AZURE_OPENAI_KEY"]
        else:
            logger.info("Using Azure OpenAI Service with Azure Developer CLI Credential")
            azure_credential = AzureDeveloperCliCredential()
            api_key = azure_credential.get_token("https://cognitiveservices.azure.com/.default").token
        openai_config = {
            "api_type": "azure",
            "api_base": f"https://{os.environ['AZURE_OPENAI_SERVICE']}.openai.azure.com",
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
        azure_credential = AzureDeveloperCliCredential()

    return SearchClient(
        endpoint=f"https://{os.environ['AZURE_SEARCH_SERVICE']}.search.windows.net",
        index_name=os.environ["AZURE_SEARCH_INDEX"],
        credential=azure_credential,
    )


def get_openai_client(oai_config: ModelConfiguration):
    if isinstance(oai_config, AzureOpenAIModelConfiguration):
        azure_token_provider = None
        if not os.environ.get("AZURE_OPENAI_KEY"):
            azure_token_provider = get_bearer_token_provider(
                AzureDeveloperCliCredential(), "https://cognitiveservices.azure.com/.default"
            )
        return openai.AzureOpenAI(
            api_version=oai_config.api_version,
            azure_endpoint=oai_config.azure_endpoint,
            api_key=oai_config.api_key if os.environ.get("AZURE_OPENAI_KEY") else None,
            azure_ad_token_provider=azure_token_provider,
            azure_deployment=oai_config.azure_deployment,
        )
    elif isinstance(oai_config, OpenAIModelConfiguration):
        oai_config: OpenAIModelConfiguration = oai_config
        return openai.OpenAI(api_key=oai_config.api_key, organization=oai_config.organization)
    else:
        raise ValueError(f"Unsupported OpenAI configuration type: {type(oai_config)}")
