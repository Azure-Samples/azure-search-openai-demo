import logging
from argparse import Namespace
from unittest.mock import AsyncMock

import openai
import openai.types
import pytest
import tenacity
from azure.core.credentials import AzureKeyCredential
from httpx import Request, Response
from openai.types.create_embedding_response import Usage

import prepdocs
from prepdocslib.embeddings import ImageEmbeddings, OpenAIEmbeddings

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
    MockAzureCredential,
)


class MockEmbeddingsClient:
    def __init__(self, create_embedding_response: openai.types.CreateEmbeddingResponse):
        self.create_embedding_response = create_embedding_response

    async def create(self, *args, **kwargs) -> openai.types.CreateEmbeddingResponse:
        return self.create_embedding_response


class MockClient:
    def __init__(self, embeddings_client):
        self.embeddings = embeddings_client


@pytest.mark.asyncio
async def test_compute_embedding_success():
    response = openai.types.CreateEmbeddingResponse(
        object="list",
        data=[
            openai.types.Embedding(
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

    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(response)),
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        disable_batch=False,
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(response)),
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        disable_batch=True,
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]


def fake_response(http_code):
    return Response(http_code, request=Request(method="get", url="https://foo.bar/"))


class RateLimitMockEmbeddingsClient:
    async def create(self, *args, **kwargs) -> openai.types.CreateEmbeddingResponse:
        raise openai.RateLimitError(
            message="Rate limited on the OpenAI embeddings API", response=fake_response(409), body=None
        )


async def create_rate_limit_client(*args, **kwargs):
    return MockClient(embeddings_client=RateLimitMockEmbeddingsClient())


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_batch(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        monkeypatch.setattr(
            "prepdocslib.embeddings.wait_random_exponential",
            lambda *args, **kwargs: tenacity.wait_fixed(0),
        )
        with pytest.raises(tenacity.RetryError):
            embeddings = OpenAIEmbeddings(
                open_ai_client=MockClient(RateLimitMockEmbeddingsClient()),
                open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
                open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
                disable_batch=False,
            )
            await embeddings.create_embeddings(texts=["foo"])
        assert caplog.text.count("Rate limited on the OpenAI embeddings API") == 14


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_single(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        monkeypatch.setattr(
            "prepdocslib.embeddings.wait_random_exponential",
            lambda *args, **kwargs: tenacity.wait_fixed(0),
        )
        with pytest.raises(tenacity.RetryError):
            embeddings = OpenAIEmbeddings(
                open_ai_client=MockClient(RateLimitMockEmbeddingsClient()),
                open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
                open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
                disable_batch=True,
            )
            await embeddings.create_embeddings(texts=["foo"])
        assert caplog.text.count("Rate limited on the OpenAI embeddings API") == 14


class AuthenticationErrorMockEmbeddingsClient:
    async def create(self, *args, **kwargs) -> openai.types.CreateEmbeddingResponse:
        raise openai.AuthenticationError(message="Bad things happened.", response=fake_response(403), body=None)


@pytest.mark.asyncio
async def test_compute_embedding_autherror(monkeypatch):
    monkeypatch.setattr(
        "prepdocslib.embeddings.wait_random_exponential",
        lambda *args, **kwargs: tenacity.wait_fixed(0),
    )
    with pytest.raises(openai.AuthenticationError):
        embeddings = OpenAIEmbeddings(
            open_ai_client=MockClient(AuthenticationErrorMockEmbeddingsClient()),
            open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
            open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            disable_batch=False,
        )
        await embeddings.create_embeddings(texts=["foo"])

    with pytest.raises(openai.AuthenticationError):
        embeddings = OpenAIEmbeddings(
            open_ai_client=MockClient(AuthenticationErrorMockEmbeddingsClient()),
            open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
            open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            disable_batch=True,
        )
        await embeddings.create_embeddings(texts=["foo"])


@pytest.mark.asyncio
async def test_image_embeddings_success(mock_azurehttp_calls):
    mock_token_provider = AsyncMock(return_value="fake_token")

    # Create the ImageEmbeddings instance
    image_embeddings = ImageEmbeddings(
        endpoint="https://fake-endpoint.azure.com/",
        token_provider=mock_token_provider,
    )

    # Call the create_embedding method with fake image bytes
    image_bytes = b"fake_image_data"
    embedding = await image_embeddings.create_embedding_for_image(image_bytes)

    # Verify the result
    assert embedding == [
        0.011925711,
        0.023533698,
        0.010133852,
        0.0063544377,
        -0.00038590943,
        0.0013952175,
        0.009054946,
        -0.033573493,
        -0.002028305,
    ]

    mock_token_provider.assert_called_once()


def test_setup_blob_manager_respects_storage_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubBlobManager:
        def __init__(
            self,
            *,
            endpoint: str,
            container: str,
            account: str,
            credential: object,
            resource_group: str,
            subscription_id: str,
            image_container: str | None = None,
        ) -> None:
            captured["endpoint"] = endpoint
            captured["container"] = container
            captured["account"] = account
            captured["credential"] = credential
            captured["resource_group"] = resource_group
            captured["subscription_id"] = subscription_id
            captured["image_container"] = image_container

    monkeypatch.setattr(prepdocs, "BlobManager", StubBlobManager)

    result = prepdocs.setup_blob_manager(
        azure_credential=MockAzureCredential(),
        storage_account="storageacct",
        storage_container="docs",
        storage_resource_group="rg",
        subscription_id="sub-id",
        storage_key="override-key",
        image_storage_container="images",
    )

    assert isinstance(result, StubBlobManager)
    assert captured["credential"] == "override-key"
    assert captured["image_container"] == "images"


def test_setup_list_file_strategy_uses_datalake_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubAdlsStrategy:
        def __init__(
            self,
            *,
            data_lake_storage_account: str,
            data_lake_filesystem: str,
            data_lake_path: str,
            credential: object,
            enable_global_documents: bool = False,
        ) -> None:
            captured["storage_account"] = data_lake_storage_account
            captured["filesystem"] = data_lake_filesystem
            captured["path"] = data_lake_path
            captured["credential"] = credential
            captured["enable_global_documents"] = enable_global_documents

    monkeypatch.setattr(prepdocs, "ADLSGen2ListFileStrategy", StubAdlsStrategy)

    strategy = prepdocs.setup_list_file_strategy(
        azure_credential=MockAzureCredential(),
        local_files=None,
        datalake_storage_account="adlsacct",
        datalake_filesystem="filesystem",
        datalake_path="path",
        datalake_key="custom-key",
        enable_global_documents=True,
    )

    assert isinstance(strategy, StubAdlsStrategy)
    assert captured["credential"] == "custom-key"
    assert captured["enable_global_documents"] is True


def test_setup_embeddings_service_populates_azure_metadata() -> None:
    embeddings = prepdocs.setup_embeddings_service(
        open_ai_client=MockClient(
            MockEmbeddingsClient(
                openai.types.CreateEmbeddingResponse(
                    object="list",
                    data=[],
                    model="text-embedding-3-large",
                    usage=Usage(prompt_tokens=0, total_tokens=0),
                )
            )
        ),
        openai_host=prepdocs.OpenAIHost.AZURE,
        emb_model_name=MOCK_EMBEDDING_MODEL_NAME,
        emb_model_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        azure_openai_deployment="deployment",
        azure_openai_endpoint="https://service.openai.azure.com",
    )

    assert isinstance(embeddings, OpenAIEmbeddings)
    assert embeddings.azure_deployment_name == "deployment"
    assert embeddings.azure_endpoint == "https://service.openai.azure.com"


def test_setup_embeddings_service_requires_endpoint_for_azure() -> None:
    with pytest.raises(ValueError):
        prepdocs.setup_embeddings_service(
            open_ai_client=MockClient(
                MockEmbeddingsClient(
                    openai.types.CreateEmbeddingResponse(
                        object="list",
                        data=[],
                        model="text-embedding-3-large",
                        usage=Usage(prompt_tokens=0, total_tokens=0),
                    )
                )
            ),
            openai_host=prepdocs.OpenAIHost.AZURE,
            emb_model_name=MOCK_EMBEDDING_MODEL_NAME,
            emb_model_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            azure_openai_deployment="deployment",
            azure_openai_endpoint=None,
        )


def test_setup_embeddings_service_requires_deployment_for_azure() -> None:
    with pytest.raises(ValueError):
        prepdocs.setup_embeddings_service(
            open_ai_client=MockClient(
                MockEmbeddingsClient(
                    openai.types.CreateEmbeddingResponse(
                        object="list",
                        data=[],
                        model="text-embedding-3-large",
                        usage=Usage(prompt_tokens=0, total_tokens=0),
                    )
                )
            ),
            openai_host=prepdocs.OpenAIHost.AZURE,
            emb_model_name=MOCK_EMBEDDING_MODEL_NAME,
            emb_model_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            azure_openai_deployment=None,
            azure_openai_endpoint="https://service.openai.azure.com",
        )


@pytest.mark.asyncio
async def test_openai_embeddings_use_deployment_for_azure_model():
    class RecordingEmbeddingsClient:
        def __init__(self) -> None:
            self.models: list[str] = []

        async def create(self, *, model: str, input, **kwargs):
            self.models.append(model)
            data = [
                openai.types.Embedding(embedding=[0.1, 0.2, 0.3], index=i, object="embedding")
                for i, _ in enumerate(input)
            ]
            return openai.types.CreateEmbeddingResponse(
                object="list",
                data=data,
                model=model,
                usage=Usage(prompt_tokens=0, total_tokens=0),
            )

    recording_client = RecordingEmbeddingsClient()
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(recording_client),
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        disable_batch=False,
        azure_deployment_name="azure-deployment",
        azure_endpoint="https://service.openai.azure.com",
    )

    result = await embeddings.create_embeddings(["foo"])

    assert recording_client.models == ["azure-deployment"]
    assert len(result) == 1


@pytest.mark.asyncio
async def test_manageacl_main_uses_search_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import manageacl as manageacl_module

    monkeypatch.setenv("AZURE_SEARCH_SERVICE", "searchsvc")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "searchindex")

    monkeypatch.setattr(manageacl_module, "load_azd_env", lambda: None)

    class DummyAzureCredential:
        def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - simple stub
            pass

    monkeypatch.setattr(manageacl_module, "AzureDeveloperCliCredential", DummyAzureCredential)

    captured: dict[str, object] = {}

    class DummyManageAcl:
        def __init__(
            self,
            *,
            service_name: str,
            index_name: str,
            url: str,
            acl_action: str,
            acl_type: str | None,
            acl: str | None,
            credentials: object,
        ) -> None:
            captured["service_name"] = service_name
            captured["index_name"] = index_name
            captured["url"] = url
            captured["credentials"] = credentials

        async def run(self) -> None:
            captured["run_called"] = True

    monkeypatch.setattr(manageacl_module, "ManageAcl", DummyManageAcl)

    args = Namespace(
        tenant_id=None,
        search_key="secret",
        url="https://example/document.pdf",
        acl_action="view",
        acl_type="oids",
        acl="user1",
    )

    await manageacl_module.main(args)

    assert captured["run_called"] is True
    assert isinstance(captured["credentials"], AzureKeyCredential)
    assert captured["credentials"].key == "secret"
    assert captured["service_name"] == "searchsvc"
    assert captured["index_name"] == "searchindex"
