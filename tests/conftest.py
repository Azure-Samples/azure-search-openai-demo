import os
from typing import IO, Any
from unittest import mock

import aiohttp
import azure.cognitiveservices.speech
import azure.storage.filedatalake
import azure.storage.filedatalake.aio
import msal
import pytest
import pytest_asyncio
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    KnowledgeBase,
    SearchField,
    SearchIndex,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
)
from azure.search.documents.knowledgebases.aio import KnowledgeBaseRetrievalClient
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from openai.types import CompletionUsage, CreateEmbeddingResponse, Embedding
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import (
    ChatCompletionMessage,
    Choice,
)
from openai.types.create_embedding_response import Usage

import app
import core
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.promptmanager import PromptManager
from core.authentication import AuthenticationHelper
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
    MockAsyncPageIterator,
    MockAsyncSearchResultsIterator,
    MockAzureCredential,
    MockAzureCredentialExpired,
    MockBlobClient,
    MockDirectoryClient,
    MockTransport,
    create_mock_retrieve,
    mock_speak_text_cancelled,
    mock_speak_text_failed,
    mock_speak_text_success,
    mock_vision_response,
)

MockSearchIndex = SearchIndex(
    name="test",
    fields=[
        SearchField(name="oids", type="Collection(Edm.String)"),
        SearchField(name="groups", type="Collection(Edm.String)"),
    ],
)
MockKnowledgeBase = KnowledgeBase(
    name="test",
    models=[],
    knowledge_sources=[
        SearchIndexKnowledgeSource(
            name="test",
            description="The default index for searching",
            search_index_parameters=SearchIndexKnowledgeSourceParameters(
                search_index_name="test", include_reference_source_data=True
            ),
        )
    ],
)


async def mock_search(self, *args, **kwargs):
    self.filter = kwargs.get("filter")
    self.access_token = kwargs.get("x_ms_query_source_authorization")
    return MockAsyncSearchResultsIterator(kwargs.get("search_text"), kwargs.get("vector_queries"))


@pytest.fixture
def mock_azurehttp_calls(monkeypatch):
    def mock_post(*args, **kwargs):
        if kwargs.get("url").endswith("computervision/retrieval:vectorizeText"):
            return mock_vision_response()
        elif kwargs.get("url").endswith("computervision/retrieval:vectorizeImage"):
            return mock_vision_response()
        else:
            raise Exception("Unexpected URL for mock call to ClientSession.post()")

    monkeypatch.setattr(aiohttp.ClientSession, "post", mock_post)


@pytest.fixture
def mock_speech_success(monkeypatch):
    monkeypatch.setattr(azure.cognitiveservices.speech.SpeechSynthesizer, "speak_text_async", mock_speak_text_success)


@pytest.fixture
def mock_speech_cancelled(monkeypatch):
    monkeypatch.setattr(azure.cognitiveservices.speech.SpeechSynthesizer, "speak_text_async", mock_speak_text_cancelled)


@pytest.fixture
def mock_speech_failed(monkeypatch):
    monkeypatch.setattr(azure.cognitiveservices.speech.SpeechSynthesizer, "speak_text_async", mock_speak_text_failed)


@pytest.fixture
def mock_openai_embedding(monkeypatch):
    async def mock_acreate(*args, **kwargs):
        return CreateEmbeddingResponse(
            object="list",
            data=[
                Embedding(
                    embedding=[
                        0.0023064255,
                        -0.009327292,
                        -0.0028842222,
                    ],
                    index=0,
                    object="embedding",
                )
            ],
            model="text-embedding-3-large",
            usage=Usage(prompt_tokens=8, total_tokens=8),
        )

    def patch(openai_client):
        monkeypatch.setattr(openai_client.embeddings, "create", mock_acreate)

    return patch


@pytest.fixture
def mock_openai_chatcompletion(monkeypatch):
    class AsyncChatCompletionIterator:
        def __init__(self, answer: str, reasoning: bool, usage: dict[str, Any]):
            chunk_id = "test-id"
            model = "gpt-4.1-mini" if not reasoning else "o3-mini"
            self.responses = [
                {"object": "chat.completion.chunk", "choices": [], "id": chunk_id, "model": model, "created": 1},
                {
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"role": "assistant"}, "index": 0, "finish_reason": None}],
                    "id": chunk_id,
                    "model": model,
                    "created": 1,
                },
            ]
            # Split at << to simulate chunked responses
            if answer.find("<<") > -1:
                parts = answer.split("<<")
                self.responses.append(
                    {
                        "object": "chat.completion.chunk",
                        "choices": [
                            {
                                "delta": {"role": "assistant", "content": parts[0] + "<<"},
                                "index": 0,
                                "finish_reason": None,
                            }
                        ],
                        "id": chunk_id,
                        "model": model,
                        "created": 1,
                    }
                )
                self.responses.append(
                    {
                        "object": "chat.completion.chunk",
                        "choices": [
                            {"delta": {"role": "assistant", "content": parts[1]}, "index": 0, "finish_reason": None}
                        ],
                        "id": chunk_id,
                        "model": model,
                        "created": 1,
                    }
                )
                self.responses.append(
                    {
                        "object": "chat.completion.chunk",
                        "choices": [{"delta": {"role": None, "content": None}, "index": 0, "finish_reason": "stop"}],
                        "id": chunk_id,
                        "model": model,
                        "created": 1,
                    }
                )
            else:
                self.responses.append(
                    {
                        "object": "chat.completion.chunk",
                        "choices": [{"delta": {"content": answer}, "index": 0, "finish_reason": None}],
                        "id": chunk_id,
                        "model": model,
                        "created": 1,
                    }
                )

            self.responses.append(
                {
                    "object": "chat.completion.chunk",
                    "choices": [],
                    "id": chunk_id,
                    "model": model,
                    "created": 1,
                    "usage": usage,
                }
            )

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.responses:
                return ChatCompletionChunk.model_validate(self.responses.pop(0))
            else:
                raise StopAsyncIteration

    async def mock_acreate(*args, **kwargs):
        # The only two possible values for seed:
        assert kwargs.get("seed") is None or kwargs.get("seed") == 42

        messages = kwargs["messages"]
        model = kwargs["model"]
        reasoning = model == "o3-mini"
        completion_usage: dict[str, any] = {
            "completion_tokens": 896,
            "prompt_tokens": 23,
            "total_tokens": 919,
            "completion_tokens_details": {
                "accepted_prediction_tokens": 0,
                "audio_tokens": 0,
                "reasoning_tokens": 384 if reasoning else 0,
                "rejected_prediction_tokens": 0,
            },
        }
        last_message_content = messages[-1]["content"]
        # Handle both old format (user message) and new format (system message with query at end)
        if isinstance(last_message_content, str):
            last_question = last_message_content
        else:
            last_question = ""
        if last_question.endswith("Generate search query for: What is the capital of France?"):
            answer = "capital of France"
        elif last_question.endswith("Generate search query for: Are interest rates high?"):
            answer = "interest rates"
        elif last_question.endswith("Generate search query for: Flowers in westbrae nursery logo?"):
            answer = "westbrae nursery logo"
        elif isinstance(last_message_content, list) and any([part.get("image_url") for part in last_message_content]):
            answer = "From the provided sources, the impact of interest rates and GDP growth on financial markets can be observed through the line graph. [Financial Market Analysis Report 2023-7.png]"
        else:
            answer = "The capital of France is Paris. [Benefit_Options-2.pdf]."
            # Check if system prompt asks for followup questions
            for msg in messages:
                if msg.get("role") == "system":
                    content = str(msg.get("content", ""))
                    print(f"DEBUG: System message content length: {len(content)}")
                    print(f"DEBUG: Contains followup?: {'Generate 3 very brief follow-up questions' in content}")
                    if "Generate 3 very brief follow-up questions" in content:
                        answer = (
                            "The capital of France is Paris. [Benefit_Options-2.pdf]. <<What is the capital of Spain?>>"
                        )
                        break
        if "stream" in kwargs and kwargs["stream"] is True:
            return AsyncChatCompletionIterator(answer, reasoning, completion_usage)
        else:
            return ChatCompletion(
                object="chat.completion",
                choices=[
                    Choice(
                        message=ChatCompletionMessage(role="assistant", content=answer), finish_reason="stop", index=0
                    )
                ],
                id="test-123",
                created=0,
                model="test-model",
                usage=CompletionUsage.model_validate(completion_usage),
            )

    def patch(openai_client):
        monkeypatch.setattr(openai_client.chat.completions, "create", mock_acreate)

    return patch


@pytest.fixture
def mock_acs_search(monkeypatch):
    monkeypatch.setattr(SearchClient, "search", mock_search)

    async def mock_get_index(*args, **kwargs):
        return MockSearchIndex

    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)


@pytest.fixture
def mock_search_knowledgebase(monkeypatch):
    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("auto"))

    async def mock_get_knowledge_base(*args, **kwargs):
        return MockKnowledgeBase

    monkeypatch.setattr(SearchIndexClient, "get_knowledge_base", mock_get_knowledge_base)


@pytest.fixture
def mock_acs_search_filter(monkeypatch):
    monkeypatch.setattr(SearchClient, "search", mock_search)

    async def mock_get_index(*args, **kwargs):
        return MockSearchIndex

    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)


@pytest.fixture
def mock_blob_container_client(monkeypatch):
    monkeypatch.setattr(ContainerClient, "get_blob_client", lambda *args, **kwargs: MockBlobClient())


@pytest.fixture
def mock_blob_container_client_exists(monkeypatch):
    async def mock_exists(*args, **kwargs):
        return True

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)


@pytest.fixture
def mock_blob_container_client_does_not_exist(monkeypatch):
    async def mock_exists(*args, **kwargs):
        return False

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)


envs = [
    {
        "OPENAI_HOST": "openai",
        "OPENAI_API_KEY": "secretkey",
        "OPENAI_ORGANIZATION": "organization",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
    },
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
    },
]

vision_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
        "USE_MULTIMODAL": "true",
        "AZURE_VISION_ENDPOINT": "https://testvision.cognitiveservices.azure.com/",
    },
]

vision_auth_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
        "USE_MULTIMODAL": "true",
        "AZURE_USE_AUTHENTICATION": "true",
        "AZURE_ENFORCE_ACCESS_CONTROL": "true",
        "AZURE_VISION_ENDPOINT": "https://testvision.cognitiveservices.azure.com/",
    },
]

auth_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
        "AZURE_USE_AUTHENTICATION": "true",
        "AZURE_ENFORCE_ACCESS_CONTROL": "true",
        "AZURE_USER_STORAGE_ACCOUNT": "test-user-storage-account",
        "AZURE_USER_STORAGE_CONTAINER": "test-user-storage-container",
        "AZURE_SERVER_APP_ID": "SERVER_APP",
        "AZURE_SERVER_APP_SECRET": "SECRET",
        "AZURE_CLIENT_APP_ID": "CLIENT_APP",
        "AZURE_TENANT_ID": "TENANT_ID",
        "USE_MULTIMODAL": "true",
        "AZURE_VISION_ENDPOINT": "https://testvision.cognitiveservices.azure.com/",
    },
]

auth_public_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
        "AZURE_USE_AUTHENTICATION": "true",
        "AZURE_ENFORCE_ACCESS_CONTROL": "true",
        "AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS": "true",
        "AZURE_ENABLE_UNAUTHENTICATED_ACCESS": "true",
        "AZURE_USER_STORAGE_ACCOUNT": "test-user-storage-account",
        "AZURE_USER_STORAGE_CONTAINER": "test-user-storage-container",
        "AZURE_SERVER_APP_ID": "SERVER_APP",
        "AZURE_SERVER_APP_SECRET": "SECRET",
        "AZURE_CLIENT_APP_ID": "CLIENT_APP",
        "AZURE_TENANT_ID": "TENANT_ID",
    },
]

reasoning_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_MODEL": "o3-mini",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "o3-mini",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
    },
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_MODEL": "o3-mini",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "o3-mini",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_REASONING_EFFORT": "low",
    },
]

knowledgebase_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_KNOWLEDGEBASE_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT": "gpt-4.1-mini",
        "USE_AGENTIC_KNOWLEDGEBASE": "true",
    },
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_KNOWLEDGEBASE_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT": "gpt-4.1-mini",
        "USE_AGENTIC_KNOWLEDGEBASE": "true",
        "USE_WEB_SOURCE": "true",
    },
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_KNOWLEDGEBASE_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT": "gpt-4.1-mini",
        "USE_AGENTIC_KNOWLEDGEBASE": "true",
        "USE_SHAREPOINT_SOURCE": "true",
    },
]

knowledgebase_auth_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_OPENAI_KNOWLEDGEBASE_MODEL": "gpt-4.1-mini",
        "AZURE_OPENAI_KNOWLEDGEBASE_DEPLOYMENT": "gpt-4.1-mini",
        "USE_AGENTIC_KNOWLEDGEBASE": "true",
        "AZURE_USE_AUTHENTICATION": "true",
        "AZURE_ENFORCE_ACCESS_CONTROL": "true",
        "AZURE_SERVER_APP_ID": "SERVER_APP",
        "AZURE_SERVER_APP_SECRET": "SECRET",
        "AZURE_CLIENT_APP_ID": "CLIENT_APP",
        "AZURE_TENANT_ID": "TENANT_ID",
    }
]


@pytest.fixture(params=envs, ids=["client0", "client1"])
def mock_env(monkeypatch, request):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_IMAGESTORAGE_CONTAINER", "test-image-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("ENABLE_LANGUAGE_PICKER", "true")
        monkeypatch.setenv("USE_SPEECH_INPUT_BROWSER", "true")
        monkeypatch.setenv("USE_SPEECH_OUTPUT_AZURE", "true")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_ID", "test-id")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_LOCATION", "eastus")
        monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4.1-mini")
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://frontend.com")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)
        if os.getenv("AZURE_USE_AUTHENTICATION") is not None:
            monkeypatch.delenv("AZURE_USE_AUTHENTICATION")

        with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest.fixture(params=reasoning_envs, ids=["reasoning_client0", "reasoning_client1"])
def mock_reasoning_env(monkeypatch, request):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("ENABLE_LANGUAGE_PICKER", "true")
        monkeypatch.setenv("USE_SPEECH_INPUT_BROWSER", "true")
        monkeypatch.setenv("USE_SPEECH_OUTPUT_AZURE", "true")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_ID", "test-id")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_LOCATION", "eastus")
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://frontend.com")
        monkeypatch.setenv("TEST_ENABLE_REASONING", "true")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)

        with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest.fixture(
    params=knowledgebase_envs,
    ids=["knowledgebase_client0", "knowledgebase_client1_web", "knowledgebase_client2_sharepoint"],
)
def mock_knowledgebase_env(monkeypatch, request):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("ENABLE_LANGUAGE_PICKER", "true")
        monkeypatch.setenv("USE_SPEECH_INPUT_BROWSER", "true")
        monkeypatch.setenv("USE_SPEECH_OUTPUT_AZURE", "true")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_KNOWLEDGEBASE_NAME", "test-search-knowledgebase")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_ID", "test-id")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_LOCATION", "eastus")
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://frontend.com")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)

        with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest.fixture(params=knowledgebase_auth_envs, ids=["knowledgebase_auth_client0"])
def mock_knowledgebase_auth_env(monkeypatch, request):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("ENABLE_LANGUAGE_PICKER", "true")
        monkeypatch.setenv("USE_SPEECH_INPUT_BROWSER", "true")
        monkeypatch.setenv("USE_SPEECH_OUTPUT_AZURE", "true")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_KNOWLEDGEBASE_NAME", "test-search-knowledgebase")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_ID", "test-id")
        monkeypatch.setenv("AZURE_SPEECH_SERVICE_LOCATION", "eastus")
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://frontend.com")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)

        with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest.fixture(params=vision_envs, ids=["client0"])
def mock_vision_env(monkeypatch, request):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_IMAGESTORAGE_CONTAINER", "test-image-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4.1-mini")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)

        with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest.fixture(params=vision_auth_envs, ids=["auth_client0"])
def mock_vision_auth_env(monkeypatch, request):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_IMAGESTORAGE_CONTAINER", "test-image-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4.1-mini")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)

        with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest_asyncio.fixture(scope="function")
async def client(
    monkeypatch,
    mock_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_blob_container_client,
    mock_azurehttp_calls,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        yield test_app.test_client()


@pytest_asyncio.fixture(scope="function")
async def reasoning_client(
    monkeypatch,
    mock_reasoning_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_blob_container_client,
    mock_azurehttp_calls,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        yield test_app.test_client()


@pytest_asyncio.fixture(scope="function")
async def knowledgebase_client(
    monkeypatch,
    mock_knowledgebase_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_search_knowledgebase,
    mock_blob_container_client,
    mock_azurehttp_calls,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        yield test_app.test_client()


@pytest_asyncio.fixture(scope="function")
async def knowledgebase_auth_client(
    monkeypatch,
    mock_knowledgebase_auth_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_search_knowledgebase,
    mock_blob_container_client,
    mock_azurehttp_calls,
    mock_confidential_client_success,
    mock_validate_token_success,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        client = test_app.test_client()
        client.config = quart_app.config

        yield client


@pytest_asyncio.fixture(scope="function")
async def client_with_expiring_token(
    monkeypatch,
    mock_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_blob_container_client,
    mock_azurehttp_calls,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        test_app.app.config.update({"azure_credential": MockAzureCredentialExpired()})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        yield test_app.test_client()


@pytest_asyncio.fixture(params=auth_envs, scope="function")
async def auth_client(
    monkeypatch,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_confidential_client_success,
    mock_validate_token_success,
    mock_acs_search_filter,
    mock_azurehttp_calls,
    request,
):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
    monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-userstorage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-userstorage-container")
    monkeypatch.setenv("USE_LOCAL_PDF_PARSER", "true")
    monkeypatch.setenv("USE_LOCAL_HTML_PARSER", "true")
    monkeypatch.setenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE", "test-documentintelligence-service")
    for key, value in request.param.items():
        monkeypatch.setenv(key, value)

    with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
        mock_default_azure_credential.return_value = MockAzureCredential()
        quart_app = app.create_app()

        async with quart_app.test_app() as test_app:
            quart_app.config.update({"TESTING": True})
            mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
            mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
            client = test_app.test_client()
            client.config = quart_app.config

            yield client


@pytest_asyncio.fixture(params=auth_public_envs, scope="function")
async def auth_public_documents_client(
    monkeypatch,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_confidential_client_success,
    mock_validate_token_success,
    mock_acs_search_filter,
    request,
):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
    monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-userstorage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-userstorage-container")
    monkeypatch.setenv("USE_LOCAL_PDF_PARSER", "true")
    monkeypatch.setenv("USE_LOCAL_HTML_PARSER", "true")
    monkeypatch.setenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE", "test-documentintelligence-service")
    monkeypatch.setenv("USE_CHAT_HISTORY_COSMOS", "true")
    monkeypatch.setenv("AZURE_COSMOSDB_ACCOUNT", "test-cosmosdb-account")
    monkeypatch.setenv("AZURE_CHAT_HISTORY_DATABASE", "test-cosmosdb-database")
    monkeypatch.setenv("AZURE_CHAT_HISTORY_CONTAINER", "test-cosmosdb-container")
    monkeypatch.setenv("AZURE_CHAT_HISTORY_VERSION", "cosmosdb-v2")

    for key, value in request.param.items():
        monkeypatch.setenv(key, value)

    with mock.patch("app.AzureDeveloperCliCredential") as mock_default_azure_credential:
        mock_default_azure_credential.return_value = MockAzureCredential()
        quart_app = app.create_app()

        async with quart_app.test_app() as test_app:
            quart_app.config.update({"TESTING": True})
            mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
            mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
            client = test_app.test_client()
            client.config = quart_app.config

            yield client


@pytest_asyncio.fixture(scope="function")
async def vision_client(
    monkeypatch,
    mock_vision_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_blob_container_client_exists,
    mock_azurehttp_calls,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_blob_service_client = BlobServiceClient(
            f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
            credential=MockAzureCredential(),
            transport=MockTransport(),
            retry_total=0,  # Necessary to avoid unnecessary network requests during tests
        )
        test_app.app.config[app.CONFIG_GLOBAL_BLOB_MANAGER].blob_service_client = mock_blob_service_client

        yield test_app.test_client()


@pytest_asyncio.fixture(scope="function")
async def vision_auth_client(
    monkeypatch,
    mock_vision_auth_env,
    mock_confidential_client_success,
    mock_validate_token_success,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_blob_container_client_exists,
    mock_azurehttp_calls,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_blob_service_client = BlobServiceClient(
            f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
            credential=MockAzureCredential(),
            transport=MockTransport(),
            retry_total=0,  # Necessary to avoid unnecessary network requests during tests
        )
        test_app.app.config[app.CONFIG_GLOBAL_BLOB_MANAGER].blob_service_client = mock_blob_service_client

        yield test_app.test_client()


@pytest.fixture
def mock_validate_token_success(monkeypatch):
    async def mock_validate_access_token(self, token):
        pass

    monkeypatch.setattr(core.authentication.AuthenticationHelper, "validate_access_token", mock_validate_access_token)


@pytest.fixture
def mock_confidential_client_success(monkeypatch):
    def mock_acquire_token_on_behalf_of(self, *args, **kwargs):
        assert kwargs.get("user_assertion") is not None
        scopes = kwargs.get("scopes")
        assert scopes == [AuthenticationHelper.scope]
        return {"access_token": "MockToken", "id_token_claims": {"oid": "OID_X"}}

    monkeypatch.setattr(
        msal.ConfidentialClientApplication, "acquire_token_on_behalf_of", mock_acquire_token_on_behalf_of
    )

    def mock_init(self, *args, **kwargs):
        pass

    monkeypatch.setattr(msal.ConfidentialClientApplication, "__init__", mock_init)


@pytest.fixture
def mock_confidential_client_unauthorized(monkeypatch):
    def mock_acquire_token_on_behalf_of(self, *args, **kwargs):
        assert kwargs.get("user_assertion") is not None
        scopes = kwargs.get("scopes")
        assert scopes == [AuthenticationHelper.scope]
        return {"error": "unauthorized"}

    monkeypatch.setattr(
        msal.ConfidentialClientApplication, "acquire_token_on_behalf_of", mock_acquire_token_on_behalf_of
    )

    def mock_init(self, *args, **kwargs):
        pass

    monkeypatch.setattr(msal.ConfidentialClientApplication, "__init__", mock_init)


@pytest.fixture
def mock_data_lake_service_client(monkeypatch):
    def mock_init(self, *args, **kwargs):
        pass

    async def mock_aenter(self, *args, **kwargs):
        return self

    async def mock_aexit(self, *args, **kwargs):
        return self

    def mock_get_file_system_client(self, *args, **kwargs):
        return azure.storage.filedatalake.FileSystemClient(account_url=None, file_system_name=None, credential=None)

    def mock_init_service_client_aio(self, *args, **kwargs):
        self.filesystems = {}

    def mock_get_file_system_client_aio(self, name, *args, **kwargs):
        if name in self.filesystems:
            return self.filesystems[name]
        self.filesystems[name] = azure.storage.filedatalake.aio.FileSystemClient(
            account_url=None, file_system_name=None, credential=None
        )
        return self.filesystems[name]

    monkeypatch.setattr(azure.storage.filedatalake.DataLakeServiceClient, "__init__", mock_init)
    monkeypatch.setattr(
        azure.storage.filedatalake.DataLakeServiceClient, "get_file_system_client", mock_get_file_system_client
    )

    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeServiceClient, "__init__", mock_init_service_client_aio)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeServiceClient, "__aenter__", mock_aenter)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeServiceClient, "__aexit__", mock_aexit)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeServiceClient, "get_file_system_client", mock_get_file_system_client_aio
    )

    def mock_init_filesystem_aio(self, *args, **kwargs):
        self.directories = {}

    def mock_get_file_client(self, path, *args, **kwargs):
        return azure.storage.filedatalake.aio.DataLakeFileClient(
            account_url=None, file_system_name=None, file_path=path, credential=None
        )

    async def mock_exists_aio(self, *args, **kwargs):
        return False

    async def mock_create_filesystem_aio(self, *args, **kwargs):
        pass

    async def mock_create_directory_aio(self, directory, *args, **kwargs):
        if directory in self.directories:
            return self.directories[directory]
        self.directories[directory] = azure.storage.filedatalake.aio.DataLakeDirectoryClient(directory)
        return self.directories[directory]

    def mock_get_root_directory_client_aio(self, *args, **kwargs):
        if "/" in self.directories:
            return self.directories["/"]
        self.directories["/"] = azure.storage.filedatalake.aio.DataLakeDirectoryClient("/")
        self.directories["/"].child_directories = self.directories
        return self.directories["/"]

    def mock_get_paths(self, *args, **kwargs):
        paths = ["a.txt", "b.txt", "c.txt"]
        if kwargs.get("path") == "OID_X":
            paths = [f"OID_X/{path}" for path in paths]
        return MockAsyncPageIterator([azure.storage.filedatalake.PathProperties(name=path) for path in paths])

    monkeypatch.setattr(azure.storage.filedatalake.FileSystemClient, "__init__", mock_init)
    monkeypatch.setattr(azure.storage.filedatalake.FileSystemClient, "get_file_client", mock_get_file_client)

    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "__init__", mock_init_filesystem_aio)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "__aenter__", mock_aenter)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "__aexit__", mock_aexit)

    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "exists", mock_exists_aio)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "get_file_client", mock_get_file_client)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient, "create_file_system", mock_create_filesystem_aio
    )
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "get_paths", mock_get_paths)

    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "create_directory", mock_create_directory_aio)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient,
        "_get_root_directory_client",
        mock_get_root_directory_client_aio,
    )

    def mock_init_file(self, *args, **kwargs):
        self.path = kwargs.get("file_path")
        self.acl = ""

    def mock_url(self, *args, **kwargs):
        return f"https://test.blob.core.windows.net/{self.path}"

    def mock_download_file(self, *args, **kwargs):
        return azure.storage.filedatalake.StorageStreamDownloader(None)

    async def mock_download_file_aio(self, *args, **kwargs):
        return azure.storage.filedatalake.aio.StorageStreamDownloader(None)

    async def mock_get_access_control(self, *args, **kwargs):
        if self.path == "a.txt":
            return {"acl": "user:A-USER-ID:r-x,group:A-GROUP-ID:r-x"}
        if self.path == "b.txt":
            return {"acl": "user:B-USER-ID:r-x,group:B-GROUP-ID:r-x"}
        if self.path == "c.txt":
            return {"acl": "user:C-USER-ID:r-x,group:C-GROUP-ID:r-x"}

        raise Exception(f"Unexpected path {self.path}")

    async def mock_upload_data_aio(self, *args, **kwargs):
        self.uploaded = True
        pass

    monkeypatch.setattr(azure.storage.filedatalake.DataLakeFileClient, "__init__", mock_init_file)
    monkeypatch.setattr(azure.storage.filedatalake.DataLakeFileClient, "download_file", mock_download_file)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeFileClient, "get_access_control", mock_get_access_control
    )
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "__init__", mock_init_file)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "url", property(mock_url))
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "__aenter__", mock_aenter)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "__aexit__", mock_aexit)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "download_file", mock_download_file_aio)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeFileClient, "get_access_control", mock_get_access_control
    )
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeFileClient, "upload_data", mock_upload_data_aio)

    def mock_init_directory(self, path, *args, **kwargs):
        self.path = path
        self.files = {}

    async def mock_get_directory_properties(self, *args, **kwargs):
        return azure.storage.filedatalake.DirectoryProperties()

    async def mock_get_access_control(self, *args, **kwargs):
        return {"owner": "OID_X"}

    def mock_directory_get_file_client(self, *args, **kwargs):
        path = kwargs.get("file")
        if path in self.files:
            return self.files[path]
        self.files[path] = azure.storage.filedatalake.aio.DataLakeFileClient(path)
        return self.files[path]

    async def mock_update_access_control_recursive_aio(self, acl, *args, **kwargs):
        for file in self.files.values():
            if len(file.acl) > 0:
                file.acl += ","
            file.acl += acl
        if self.path == "/":
            for directory in self.child_directories.values():
                await mock_update_access_control_recursive_aio(directory, acl)

    async def mock_close_aio(self, *args, **kwargs):
        pass

    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeDirectoryClient, "__init__", mock_init_directory)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeDirectoryClient, "__aenter__", mock_aenter)
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeDirectoryClient, "__aexit__", mock_aexit)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeDirectoryClient, "get_file_client", mock_directory_get_file_client
    )
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeDirectoryClient,
        "update_access_control_recursive",
        mock_update_access_control_recursive_aio,
    )
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeDirectoryClient,
        "get_directory_properties",
        mock_get_directory_properties,
    )
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.DataLakeDirectoryClient, "get_access_control", mock_get_access_control
    )
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeDirectoryClient, "close", mock_close_aio)

    def mock_readinto(self, stream: IO[bytes]):
        stream.write(b"texttext")
        return 8

    monkeypatch.setattr(azure.storage.filedatalake.StorageStreamDownloader, "__init__", mock_init)
    monkeypatch.setattr(azure.storage.filedatalake.StorageStreamDownloader, "readinto", mock_readinto)

    monkeypatch.setattr(azure.storage.filedatalake.aio.StorageStreamDownloader, "__init__", mock_init)
    monkeypatch.setattr(azure.storage.filedatalake.aio.StorageStreamDownloader, "readinto", mock_readinto)


@pytest.fixture
def mock_user_directory_client(monkeypatch):
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient,
        "get_directory_client",
        lambda *args, **kwargs: MockDirectoryClient(),
    )


@pytest.fixture
def chat_approach():
    return ChatReadRetrieveReadApproach(
        search_client=SearchClient(endpoint="", index_name="", credential=AzureKeyCredential("")),
        search_index_name=None,
        knowledgebase_model=None,
        knowledgebase_deployment=None,
        knowledgebase_client=None,
        openai_client=None,
        chatgpt_model="gpt-4.1-mini",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        embedding_field="embedding3",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
        prompt_manager=PromptManager(),
        user_blob_manager=AdlsBlobManager(
            endpoint="https://test-userstorage-account.dfs.core.windows.net",
            container="test-userstorage-container",
            credential=MockAzureCredential(),
        ),
        global_blob_manager=BlobManager(  # on normal Azure storage
            endpoint="https://test-globalstorage-account.blob.core.windows.net",
            container="test-globalstorage-container",
            credential=MockAzureCredential(),
        ),
    )
