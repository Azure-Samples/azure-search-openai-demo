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

from prepdocslib.embeddings import ImageEmbeddings, OpenAIEmbeddings

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
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
