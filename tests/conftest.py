import argparse
import json
import os
from unittest import mock

import aiohttp
import azure.storage.filedatalake
import azure.storage.filedatalake.aio
import msal
import pytest
import pytest_asyncio
from azure.keyvault.secrets.aio import SecretClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import SearchField, SearchIndex
from azure.storage.blob.aio import ContainerClient
from openai.types import CreateEmbeddingResponse, Embedding
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import (
    ChatCompletionMessage,
    Choice,
)
from openai.types.create_embedding_response import Usage

import app
import core
from core.authentication import AuthenticationHelper

from .mocks import (
    MockAsyncSearchResultsIterator,
    MockAzureCredential,
    MockBlobClient,
    MockKeyVaultSecretClient,
    MockResponse,
    mock_computervision_response,
)

MockSearchIndex = SearchIndex(
    name="test",
    fields=[
        SearchField(name="oids", type="Collection(Edm.String)"),
        SearchField(name="groups", type="Collection(Edm.String)"),
    ],
)


async def mock_search(self, *args, **kwargs):
    self.filter = kwargs.get("filter")
    return MockAsyncSearchResultsIterator(kwargs.get("search_text"), kwargs.get("vector_queries"))


@pytest.fixture
def mock_get_secret(monkeypatch):
    monkeypatch.setattr(SecretClient, "get_secret", MockKeyVaultSecretClient().get_secret)


@pytest.fixture
def mock_compute_embeddings_call(monkeypatch):
    def mock_post(*args, **kwargs):
        if kwargs.get("url").endswith("computervision/retrieval:vectorizeText"):
            return mock_computervision_response()
        else:
            raise Exception("Unexpected URL for mock call to ClientSession.post()")

    monkeypatch.setattr(aiohttp.ClientSession, "post", mock_post)


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
            model="text-embedding-ada-002",
            usage=Usage(prompt_tokens=8, total_tokens=8),
        )

    def patch(openai_client):
        monkeypatch.setattr(openai_client.embeddings, "create", mock_acreate)

    return patch


@pytest.fixture
def mock_openai_chatcompletion(monkeypatch):
    class AsyncChatCompletionIterator:
        def __init__(self, answer: str):
            chunk_id = "test-id"
            model = "gpt-35-turbo"
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

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.responses:
                return ChatCompletionChunk.model_validate(self.responses.pop(0))
            else:
                raise StopAsyncIteration

    async def mock_acreate(*args, **kwargs):
        messages = kwargs["messages"]
        last_question = messages[-1]["content"]
        if last_question == "Generate search query for: What is the capital of France?":
            answer = "capital of France"
        elif last_question == "Generate search query for: Are interest rates high?":
            answer = "interest rates"
        elif isinstance(last_question, list) and last_question[2].get("image_url"):
            answer = "From the provided sources, the impact of interest rates and GDP growth on financial markets can be observed through the line graph. [Financial Market Analysis Report 2023-7.png]"
        else:
            answer = "The capital of France is Paris. [Benefit_Options-2.pdf]."
            if messages[0]["content"].find("Generate 3 very brief follow-up questions") > -1:
                answer = "The capital of France is Paris. [Benefit_Options-2.pdf]. <<What is the capital of Spain?>>"
        if "stream" in kwargs and kwargs["stream"] is True:
            return AsyncChatCompletionIterator(answer)
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
            )

    def patch(openai_client):
        monkeypatch.setattr(openai_client.chat.completions, "create", mock_acreate)

    return patch


@pytest.fixture
def mock_acs_search(monkeypatch):
    monkeypatch.setattr(SearchClient, "search", mock_search)
    monkeypatch.setattr(SearchClient, "search", mock_search)

    async def mock_get_index(*args, **kwargs):
        return MockSearchIndex

    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)


@pytest.fixture
def mock_acs_search_filter(monkeypatch):
    monkeypatch.setattr(SearchClient, "search", mock_search)

    async def mock_get_index(*args, **kwargs):
        return MockSearchIndex

    monkeypatch.setattr(SearchIndexClient, "get_index", mock_get_index)


@pytest.fixture
def mock_blob_container_client(monkeypatch):
    monkeypatch.setattr(ContainerClient, "get_blob_client", lambda *args, **kwargs: MockBlobClient())


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
        "USE_GPT4V": "true",
        "AZURE_OPENAI_GPT4V_MODEL": "gpt-4",
        "VISION_SECRET_NAME": "mysecret",
        "VISION_ENDPOINT": "https://testvision.cognitiveservices.azure.com/",
        "AZURE_KEY_VAULT_NAME": "mykeyvault",
    },
]

auth_envs = [
    {
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai-service",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "test-chatgpt",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "test-ada",
        "AZURE_USE_AUTHENTICATION": "true",
        "AZURE_SERVER_APP_ID": "SERVER_APP",
        "AZURE_SERVER_APP_SECRET": "SECRET",
        "AZURE_CLIENT_APP_ID": "CLIENT_APP",
        "AZURE_TENANT_ID": "TENANT_ID",
    },
]


@pytest.fixture(params=envs, ids=["client0", "client1"])
def mock_env(monkeypatch, request, mock_get_secret):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_STORAGE_RESOURCE_GROUP", "test-storage-rg")
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-storage-subid")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-35-turbo")
        monkeypatch.setenv("ALLOWED_ORIGIN", "https://frontend.com")
        for key, value in request.param.items():
            monkeypatch.setenv(key, value)
        if os.getenv("AZURE_USE_AUTHENTICATION") is not None:
            monkeypatch.delenv("AZURE_USE_AUTHENTICATION")

        with mock.patch("app.DefaultAzureCredential") as mock_default_azure_credential:
            mock_default_azure_credential.return_value = MockAzureCredential()
            yield


@pytest_asyncio.fixture()
async def client(
    monkeypatch,
    mock_env,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_acs_search,
    mock_blob_container_client,
    mock_compute_embeddings_call,
):
    quart_app = app.create_app()

    async with quart_app.test_app() as test_app:
        test_app.app.config.update({"TESTING": True})
        mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
        yield test_app.test_client()


@pytest_asyncio.fixture(params=auth_envs)
async def auth_client(
    monkeypatch,
    mock_openai_chatcompletion,
    mock_openai_embedding,
    mock_confidential_client_success,
    mock_validate_token_success,
    mock_list_groups_success,
    mock_acs_search_filter,
    mock_get_secret,
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
            mock_openai_chatcompletion(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
            mock_openai_embedding(test_app.app.config[app.CONFIG_OPENAI_CLIENT])
            client = test_app.test_client()
            client.config = quart_app.config

            yield client


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

    class AsyncListIterator:
        def __init__(self, input_list):
            self.input_list = input_list
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index < len(self.input_list):
                value = self.input_list[self.index]
                self.index += 1
                return value
            else:
                raise StopAsyncIteration

    async def mock_get_paths(self, *args, **kwargs):
        yield argparse.Namespace(is_directory=False, name="a.txt")
        yield argparse.Namespace(is_directory=False, name="b.txt")
        yield argparse.Namespace(is_directory=False, name="c.txt")

    monkeypatch.setattr(azure.storage.filedatalake.FileSystemClient, "__init__", mock_init)
    monkeypatch.setattr(azure.storage.filedatalake.FileSystemClient, "get_file_client", mock_get_file_client)

    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "__init__", mock_init_filesystem_aio)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "__aenter__", mock_aenter)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "__aexit__", mock_aexit)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "get_paths", mock_get_paths)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "exists", mock_exists_aio)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "get_paths", mock_get_paths)
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "get_file_client", mock_get_file_client)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient, "create_file_system", mock_create_filesystem_aio
    )
    monkeypatch.setattr(azure.storage.filedatalake.aio.FileSystemClient, "create_directory", mock_create_directory_aio)
    monkeypatch.setattr(
        azure.storage.filedatalake.aio.FileSystemClient,
        "_get_root_directory_client",
        mock_get_root_directory_client_aio,
    )

    def mock_init_file(self, *args, **kwargs):
        self.path = kwargs.get("file_path")
        self.acl = ""

    def mock_download_file(self, *args, **kwargs):
        return azure.storage.filedatalake.StorageStreamDownloader(None)

    def mock_download_file_aio(self, *args, **kwargs):
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
    monkeypatch.setattr(azure.storage.filedatalake.aio.DataLakeDirectoryClient, "close", mock_close_aio)

    def mock_readinto(self, *args, **kwargs):
        pass

    monkeypatch.setattr(azure.storage.filedatalake.StorageStreamDownloader, "__init__", mock_init)
    monkeypatch.setattr(azure.storage.filedatalake.StorageStreamDownloader, "readinto", mock_readinto)

    monkeypatch.setattr(azure.storage.filedatalake.aio.StorageStreamDownloader, "__init__", mock_init)
    monkeypatch.setattr(azure.storage.filedatalake.aio.StorageStreamDownloader, "readinto", mock_readinto)
