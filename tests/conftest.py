import json
from collections import namedtuple
from unittest import mock

import aiohttp
import msal
import openai
import pytest
import pytest_asyncio
from azure.search.documents.aio import SearchClient

import app
from core.authentication import AuthenticationHelper

MockToken = namedtuple("MockToken", ["token", "expires_on"])


class MockAzureCredential:
    async def get_token(self, uri):
        return MockToken("mock_token", 9999999999)


@pytest.fixture
def mock_openai_embedding(monkeypatch):
    async def mock_acreate(*args, **kwargs):
        if openai.api_type == "openai":
            assert kwargs.get("deployment_id") is None
        else:
            assert kwargs.get("deployment_id") is not None
        return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    monkeypatch.setattr(openai.Embedding, "acreate", mock_acreate)


@pytest.fixture
def mock_openai_chatcompletion(monkeypatch):
    class AsyncChatCompletionIterator:
        def __init__(self, answer):
            self.num = 1
            self.answer = answer

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.num == 1:
                self.num = 0
                return openai.util.convert_to_openai_object({"choices": [{"delta": {"content": self.answer}}]})
            else:
                raise StopAsyncIteration

    async def mock_acreate(*args, **kwargs):
        if openai.api_type == "openai":
            assert kwargs.get("deployment_id") is None
        else:
            assert kwargs.get("deployment_id") is not None
        messages = kwargs["messages"]
        if messages[-1]["content"] == "Generate search query for: What is the capital of France?":
            answer = "capital of France"
        else:
            answer = "The capital of France is Paris."
        if "stream" in kwargs and kwargs["stream"] is True:
            return AsyncChatCompletionIterator(answer)
        else:
            return openai.util.convert_to_openai_object({"choices": [{"message": {"content": answer}}]})

    monkeypatch.setattr(openai.ChatCompletion, "acreate", mock_acreate)


@pytest.fixture
def mock_acs_search(monkeypatch):
    class Caption:
        def __init__(self, text):
            self.text = text

    class AsyncSearchResultsIterator:
        def __init__(self):
            self.num = 1

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.num == 1:
                self.num = 0
                return {
                    "sourcepage": "Benefit_Options-2.pdf",
                    "sourcefile": "Benefit_Options.pdf",
                    "content": "There is a whistleblower policy.",
                    "embeddings": [],
                    "category": None,
                    "id": "file-Benefit_Options_pdf-42656E656669745F4F7074696F6E732E706466-page-2",
                    "@search.score": 0.03279569745063782,
                    "@search.reranker_score": 3.4577205181121826,
                    "@search.highlights": None,
                    "@search.captions": [Caption("Caption: A whistleblower policy.")],
                }
            else:
                raise StopAsyncIteration

    async def mock_search(*args, **kwargs):
        return AsyncSearchResultsIterator()

    monkeypatch.setattr(SearchClient, "search", mock_search)


@pytest.fixture
def mock_acs_search_filter(monkeypatch):
    class AsyncSearchResultsIterator:
        def __init__(self):
            self.num = 1

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    async def mock_search(*args, **kwargs):
        monkeypatch.setenv("FILTER", kwargs.get("filter"))
        return AsyncSearchResultsIterator()

    monkeypatch.setattr(SearchClient, "search", mock_search)


envs = [
    {
        "OPENAI_HOST": "openai",
        "OPENAI_API_KEY": "secretkey",
        "OPENAI_ORGANIZATION": "organization",
    },
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
    },
]

auth_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_USE_AUTHENTICATION": True,
        "AZURE_SERVER_APP_ID": "SERVER_APP",
        "AZURE_SERVER_APP_SECRET": "SECRET",
        "AZURE_CLIENT_APP_ID": "CLIENT_APP",
        "AZURE_TENANT_ID": "TENANT_ID",
    },
]


@pytest_asyncio.fixture(params=envs)
async def client(monkeypatch, mock_openai_chatcompletion, mock_openai_embedding, mock_acs_search, request):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
    monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-35-turbo")
    for key, value in request.param.items():
        monkeypatch.setenv(key, value)

    with mock.patch("app.DefaultAzureCredential") as mock_default_azure_credential:
        mock_default_azure_credential.return_value = MockAzureCredential()
        quart_app = app.create_app()

        async with quart_app.test_app() as test_app:
            quart_app.config.update({"TESTING": True})

            yield test_app.test_client()


@pytest_asyncio.fixture(params=auth_envs)
async def auth_client(
    monkeypatch,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_confidential_client_success,
    mock_list_groups_success,
    mock_acs_search_filter,
    request,
):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
    monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-35-turbo")
    for key, value in request.param.items():
        monkeypatch.setenv(key, value)

    with mock.patch("app.DefaultAzureCredential") as mock_default_azure_credential:
        mock_default_azure_credential.return_value = MockAzureCredential()
        quart_app = app.create_app()

        async with quart_app.test_app() as test_app:
            quart_app.config.update({"TESTING": True})

            yield test_app.test_client()


@pytest.fixture
def mock_confidential_client_success(monkeypatch):
    def mock_acquire_token_on_behalf_of(self, *args, **kwargs):
        assert kwargs.get("user_assertion") is not None
        scopes = kwargs.get("scopes")
        assert scopes == [AuthenticationHelper.scope]
        return {"access_token": "MockToken", "id_token_claims": {"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]}}

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
def mock_confidential_client_overage(monkeypatch):
    def mock_acquire_token_on_behalf_of(self, *args, **kwargs):
        assert kwargs.get("user_assertion") is not None
        scopes = kwargs.get("scopes")
        assert scopes == [AuthenticationHelper.scope]
        return {
            "access_token": "MockToken",
            "id_token_claims": {
                "oid": "OID_X",
                "_claim_names": {"groups": "src1"},
                "_claim_sources": {"src1": {"endpoint": "https://example.com"}},
            },
        }

    monkeypatch.setattr(
        msal.ConfidentialClientApplication, "acquire_token_on_behalf_of", mock_acquire_token_on_behalf_of
    )

    def mock_init(self, *args, **kwargs):
        pass

    monkeypatch.setattr(msal.ConfidentialClientApplication, "__init__", mock_init)


class MockResponse:
    def __init__(self, text, status):
        self.text = text
        self.status = status

    async def text(self):
        return self._text

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self

    async def json(self):
        return json.loads(self.text)


@pytest.fixture
def mock_list_groups_success(monkeypatch):
    class MockListResponse:
        def __init__(self):
            self.num = 2

        def run(self, *args, **kwargs):
            if self.num == 2:
                self.num = 1
                return MockResponse(
                    text=json.dumps(
                        {"@odata.nextLink": "https://odatanextlink.com", "value": [{"id": "OVERAGE_GROUP_Y"}]}
                    ),
                    status=200,
                )
            if self.num == 1:
                assert kwargs.get("url") == "https://odatanextlink.com"
                self.num = 0
                return MockResponse(text=json.dumps({"value": [{"id": "OVERAGE_GROUP_Z"}]}), status=200)

            raise Exception("too many runs")

    mock_list_response = MockListResponse()

    def mock_get(*args, **kwargs):
        return mock_list_response.run(*args, **kwargs)

    monkeypatch.setattr(aiohttp.ClientSession, "get", mock_get)


@pytest.fixture
def mock_list_groups_unauthorized(monkeypatch):
    class MockListResponse:
        def __init__(self):
            self.num = 1

        def run(self, *args, **kwargs):
            if self.num == 1:
                self.num = 0
                return MockResponse(text=json.dumps({"error": "unauthorized"}), status=401)

            raise Exception("too many runs")

    mock_list_response = MockListResponse()

    def mock_get(*args, **kwargs):
        return mock_list_response.run(*args, **kwargs)

    monkeypatch.setattr(aiohttp.ClientSession, "get", mock_get)
