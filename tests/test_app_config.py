import os
from unittest import mock

import pytest
import quart

import app


@pytest.fixture
def minimal_env(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
        monkeypatch.setenv("AZURE_OPENAI_SERVICE", "test-openai-service")
        monkeypatch.setenv("AZURE_OPENAI_CHATGPT_MODEL", "gpt-35-turbo")
        yield


@pytest.mark.asyncio
async def test_app_local_openai(monkeypatch, minimal_env):
    monkeypatch.setenv("OPENAI_HOST", "local")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:5000")

    quart_app = app.create_app()
    async with quart_app.test_app():
        assert quart_app.config[app.CONFIG_OPENAI_CLIENT].api_key == "no-key-required"
        assert quart_app.config[app.CONFIG_OPENAI_CLIENT].base_url == "http://localhost:5000"


@pytest.mark.asyncio
async def test_app_azure_custom_key(monkeypatch, minimal_env):
    monkeypatch.setenv("OPENAI_HOST", "azure_custom")
    monkeypatch.setenv("AZURE_OPENAI_CUSTOM_URL", "http://azureapi.com/api/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY_OVERRIDE", "azure-api-key")

    quart_app = app.create_app()
    async with quart_app.test_app():
        assert quart_app.config[app.CONFIG_OPENAI_CLIENT].api_key == "azure-api-key"
        assert quart_app.config[app.CONFIG_OPENAI_CLIENT].base_url == "http://azureapi.com/api/v1/openai/"


@pytest.mark.asyncio
async def test_app_azure_custom_identity(monkeypatch, minimal_env):
    monkeypatch.setenv("OPENAI_HOST", "azure_custom")
    monkeypatch.setenv("AZURE_OPENAI_CUSTOM_URL", "http://azureapi.com/api/v1")

    quart_app = app.create_app()
    async with quart_app.test_app():
        assert quart_app.config[app.CONFIG_OPENAI_CLIENT].api_key == "<missing API key>"
        assert quart_app.config[app.CONFIG_OPENAI_CLIENT].base_url == "http://azureapi.com/api/v1/openai/"


@pytest.mark.asyncio
async def test_app_user_upload_processors(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")

    quart_app = app.create_app()
    async with quart_app.test_app():
        ingester = quart_app.config[app.CONFIG_INGESTER]
        assert ingester is not None
        assert len(ingester.file_processors.keys()) == 6


@pytest.mark.asyncio
async def test_app_user_upload_processors_docint(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE", "test-docint-service")

    quart_app = app.create_app()
    async with quart_app.test_app():
        ingester = quart_app.config[app.CONFIG_INGESTER]
        assert ingester is not None
        assert len(ingester.file_processors.keys()) == 15


@pytest.mark.asyncio
async def test_app_user_upload_processors_docint_localpdf(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE", "test-docint-service")
    monkeypatch.setenv("USE_LOCAL_PDF_PARSER", "true")

    quart_app = app.create_app()
    async with quart_app.test_app():
        ingester = quart_app.config[app.CONFIG_INGESTER]
        assert ingester is not None
        assert len(ingester.file_processors.keys()) == 15
        assert ingester.file_processors[".pdf"] is not ingester.file_processors[".pptx"]


@pytest.mark.asyncio
async def test_app_user_upload_processors_docint_localhtml(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE", "test-docint-service")
    monkeypatch.setenv("USE_LOCAL_HTML_PARSER", "true")

    quart_app = app.create_app()
    async with quart_app.test_app():
        ingester = quart_app.config[app.CONFIG_INGESTER]
        assert ingester is not None
        assert len(ingester.file_processors.keys()) == 15
        assert ingester.file_processors[".html"] is not ingester.file_processors[".pptx"]


@pytest.mark.asyncio
async def test_app_config_default(monkeypatch, minimal_env):
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is True
        assert result["showVectorOption"] is True


@pytest.mark.asyncio
async def test_app_config_use_vectors_true(monkeypatch, minimal_env):
    monkeypatch.setenv("USE_VECTORS", "true")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is True
        assert result["showVectorOption"] is True


@pytest.mark.asyncio
async def test_app_config_use_vectors_false(monkeypatch, minimal_env):
    monkeypatch.setenv("USE_VECTORS", "false")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is True
        assert result["showVectorOption"] is False


@pytest.mark.asyncio
async def test_app_config_semanticranker_free(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_SEARCH_SEMANTIC_RANKER", "free")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is True
        assert result["showVectorOption"] is True
        assert result["showUserUpload"] is False


@pytest.mark.asyncio
async def test_app_config_semanticranker_disabled(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_SEARCH_SEMANTIC_RANKER", "disabled")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is False
        assert result["showVectorOption"] is True
        assert result["showUserUpload"] is False


@pytest.mark.asyncio
async def test_app_config_user_upload(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is True
        assert result["showVectorOption"] is True
        assert result["showUserUpload"] is True


@pytest.mark.asyncio
async def test_app_config_user_upload_novectors(monkeypatch, minimal_env):
    """Check that this combo works correctly with prepdocs.py embedding service."""
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("USE_VECTORS", "false")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showGPT4VOptions"] is False
        assert result["showSemanticRankerOption"] is True
        assert result["showVectorOption"] is False
        assert result["showUserUpload"] is True


@pytest.mark.asyncio
async def test_app_config_user_upload_bad_openai_config(monkeypatch, minimal_env):
    """Check that this combo works correctly with prepdocs.py embedding service."""
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("OPENAI_HOST", "openai")
    quart_app = app.create_app()
    with pytest.raises(
        quart.testing.app.LifespanError, match="OpenAI key is required when using the non-Azure OpenAI API"
    ):
        async with quart_app.test_app() as test_app:
            test_app.test_client()


@pytest.mark.asyncio
async def test_app_config_user_upload_openaicom(monkeypatch, minimal_env):
    """Check that this combo works correctly with prepdocs.py embedding service."""
    monkeypatch.setenv("AZURE_USERSTORAGE_ACCOUNT", "test-user-storage-account")
    monkeypatch.setenv("AZURE_USERSTORAGE_CONTAINER", "test-user-storage-container")
    monkeypatch.setenv("USE_USER_UPLOAD", "true")
    monkeypatch.setenv("OPENAI_HOST", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "pretendkey")
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        client = test_app.test_client()
        response = await client.get("/config")
        assert response.status_code == 200
        result = await response.get_json()
        assert result["showUserUpload"] is True


@pytest.mark.asyncio
async def test_app_config_for_client(client):
    response = await client.get("/config")
    assert response.status_code == 200
    result = await response.get_json()
    assert result["showGPT4VOptions"] == (os.getenv("USE_GPT4V") == "true")
    assert result["showSemanticRankerOption"] is True
    assert result["showVectorOption"] is True
