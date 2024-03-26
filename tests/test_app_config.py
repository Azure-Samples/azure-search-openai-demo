import os
from unittest import mock

import pytest
from azure.keyvault.secrets.aio import SecretClient

import app

from .mocks import MockKeyVaultSecret


@pytest.fixture
def minimal_env(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "test-storage-account")
        monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "test-storage-container")
        monkeypatch.setenv("AZURE_SEARCH_INDEX", "test-search-index")
        monkeypatch.setenv("AZURE_SEARCH_SERVICE", "test-search-service")
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


@pytest.mark.asyncio
async def test_app_config_for_client(client):
    response = await client.get("/config")
    assert response.status_code == 200
    result = await response.get_json()
    assert result["showGPT4VOptions"] == (os.getenv("USE_GPT4V") == "true")
    assert result["showSemanticRankerOption"] is True
    assert result["showVectorOption"] is True


@pytest.mark.asyncio
async def test_app_visionkey_notfound(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_KEY_VAULT_NAME", "my_key_vault")
    monkeypatch.setenv("VISION_SECRET_NAME", "")
    monkeypatch.setenv("AZURE_SEARCH_SECRET_NAME", "search-secret-name")

    async def get_secret(*args, **kwargs):
        if args[1] == "vision-secret-name":
            raise Exception("Key not found")
        return MockKeyVaultSecret("mysecret")

    monkeypatch.setattr(SecretClient, "get_secret", get_secret)

    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        test_app.test_client()


@pytest.mark.asyncio
async def test_app_searchkey_notfound(monkeypatch, minimal_env):
    monkeypatch.setenv("AZURE_KEY_VAULT_NAME", "my_key_vault")
    monkeypatch.setenv("VISION_SECRET_NAME", "vision-secret-name")
    monkeypatch.setenv("AZURE_SEARCH_SECRET_NAME", "")

    async def get_secret(*args, **kwargs):
        if args[1] == "search-secret-name":
            raise Exception("Key not found")
        return MockKeyVaultSecret("mysecret")

    monkeypatch.setattr(SecretClient, "get_secret", get_secret)

    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        test_app.test_client()
