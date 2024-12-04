import os
import asyncio
import json
import logging
import dataclasses
from typing import Any, AsyncGenerator, Dict, Union, cast
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from error import error_dict
from core.authentication import AuthenticationHelper
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from guardrails import GuardrailsOrchestrator, ProvanityCheck, NSFWCheck, DetectPIICheck, BanListCheck
from quart import make_response


azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
AZURE_SEARCH_SERVICE = os.environ["AZURE_SEARCH_SERVICE"]
AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
OPENAI_CHATGPT_MODEL = os.environ["AZURE_OPENAI_CHATGPT_MODEL"]
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
OPENAI_EMB_MODEL = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
KB_FIELDS_SOURCEPAGE = os.getenv("KB_FIELDS_SOURCEPAGE", "sourcepage")
KB_FIELDS_CONTENT = os.getenv("KB_FIELDS_CONTENT", "content")
AZURE_SEARCH_QUERY_LANGUAGE = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")
AZURE_SEARCH_QUERY_SPELLER = os.getenv("AZURE_SEARCH_QUERY_SPELLER", "lexicon")
OPENAI_EMB_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "1536"))
AZURE_USE_AUTHENTICATION = False
AZURE_SERVER_APP_ID = os.getenv("AZURE_SERVER_APP_ID")
AZURE_SERVER_APP_SECRET = os.getenv("AZURE_SERVER_APP_SECRET")
AZURE_CLIENT_APP_ID = os.getenv("AZURE_CLIENT_APP_ID")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_AUTH_TENANT_ID = os.getenv("AZURE_AUTH_TENANT_ID", AZURE_TENANT_ID)
AZURE_ENFORCE_ACCESS_CONTROL = False
AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS = False
AZURE_ENABLE_UNAUTHENTICATED_ACCESS = False


async def format_as_ndjson(r: AsyncGenerator[dict, None]) -> AsyncGenerator[str, None]:
    try:
        async for event in r:
            yield json.dumps(event, ensure_ascii=False, cls=JSONEncoder) + "\n"
    except Exception as error:
        logging.exception("Exception while generating response stream: %s", error)
        yield json.dumps(error_dict(error))


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            return dataclasses.asdict(o)
        return super().default(o)


async def main():
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=AZURE_SEARCH_INDEX,
        credential=azure_credential,
    )

    endpoint = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
    api_key = os.getenv("OPENAI_API_KEY")
    api_version = "2024-06-01"
    openai_client = AsyncAzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=api_key)

    search_index_client = SearchIndexClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        credential=azure_credential,
    )
    search_index = await search_index_client.get_index(AZURE_SEARCH_INDEX)

    auth_helper = AuthenticationHelper(
        search_index=search_index,
        use_authentication=AZURE_USE_AUTHENTICATION,
        server_app_id=AZURE_SERVER_APP_ID,
        server_app_secret=AZURE_SERVER_APP_SECRET,
        client_app_id=AZURE_CLIENT_APP_ID,
        tenant_id=AZURE_AUTH_TENANT_ID,
        require_access_control=AZURE_ENFORCE_ACCESS_CONTROL,
        enable_global_documents=AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS,
        enable_unauthenticated_access=AZURE_ENABLE_UNAUTHENTICATED_ACCESS,
    )

    input_guardrails = GuardrailsOrchestrator(openai_client=openai_client, guardrails=[BanListCheck(["Christopher"])])

    approach = ChatReadRetrieveReadApproach(
        search_client=search_client,
        openai_client=openai_client,
        auth_helper=auth_helper,
        chatgpt_model=OPENAI_CHATGPT_MODEL,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=OPENAI_EMB_MODEL,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        embedding_dimensions=OPENAI_EMB_DIMENSIONS,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
        input_guardrails=input_guardrails,
    )

    message = [{"role": "user", "content": "hello Christopher"}]
    result = await approach.run_stream(message)
    async for event_chunk in result:
        print(event_chunk)


if __name__ == "__main__":
    asyncio.run(main())
