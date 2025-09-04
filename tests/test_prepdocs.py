import logging
from unittest.mock import AsyncMock

import openai
import openai.types
import pytest
import tenacity
from httpx import Request, Response
from openai.types.create_embedding_response import Usage

from prepdocslib.embeddings import (
    AzureOpenAIEmbeddingService,
    ImageEmbeddings,
    OpenAIEmbeddingService,
)

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
async def test_compute_embedding_success(monkeypatch):
    async def mock_create_client(*args, **kwargs):
        # From https://platform.openai.com/docs/api-reference/embeddings/create
        return MockClient(
            embeddings_client=MockEmbeddingsClient(
                create_embedding_response=openai.types.CreateEmbeddingResponse(
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
            )
        )

    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        open_ai_api_version="test-api-version",
        credential=MockAzureCredential(),
        disable_batch=False,
    )
    monkeypatch.setattr(embeddings, "create_client", mock_create_client)
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        open_ai_api_version="test-api-version",
        credential=MockAzureCredential(),
        disable_batch=True,
    )
    monkeypatch.setattr(embeddings, "create_client", mock_create_client)
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddingService(
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        credential=MockAzureCredential(),
        organization="org",
        disable_batch=False,
    )
    monkeypatch.setattr(embeddings, "create_client", mock_create_client)
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddingService(
        open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
        open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        credential=MockAzureCredential(),
        organization="org",
        disable_batch=True,
    )
    monkeypatch.setattr(embeddings, "create_client", mock_create_client)
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
        monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
        with pytest.raises(tenacity.RetryError):
            embeddings = AzureOpenAIEmbeddingService(
                open_ai_service="x",
                open_ai_deployment="x",
                open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
                open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
                open_ai_api_version="test-api-version",
                credential=MockAzureCredential(),
                disable_batch=False,
            )
            monkeypatch.setattr(embeddings, "create_client", create_rate_limit_client)
            await embeddings.create_embeddings(texts=["foo"])
        assert caplog.text.count("Rate limited on the OpenAI embeddings API") == 14


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_single(monkeypatch, caplog):
    with caplog.at_level(logging.INFO):
        monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
        with pytest.raises(tenacity.RetryError):
            embeddings = AzureOpenAIEmbeddingService(
                open_ai_service="x",
                open_ai_deployment="x",
                open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
                open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
                open_ai_api_version="test-api-version",
                credential=MockAzureCredential(),
                disable_batch=True,
            )
            monkeypatch.setattr(embeddings, "create_client", create_rate_limit_client)
            await embeddings.create_embeddings(texts=["foo"])
        assert caplog.text.count("Rate limited on the OpenAI embeddings API") == 14


class AuthenticationErrorMockEmbeddingsClient:
    async def create(self, *args, **kwargs) -> openai.types.CreateEmbeddingResponse:
        raise openai.AuthenticationError(message="Bad things happened.", response=fake_response(403), body=None)


async def create_auth_error_limit_client(*args, **kwargs):
    return MockClient(embeddings_client=AuthenticationErrorMockEmbeddingsClient())


@pytest.mark.asyncio
async def test_compute_embedding_autherror(monkeypatch, capsys):
    monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
    with pytest.raises(openai.AuthenticationError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
            open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            open_ai_api_version="test-api-version",
            credential=MockAzureCredential(),
            disable_batch=False,
        )
        monkeypatch.setattr(embeddings, "create_client", create_auth_error_limit_client)
        await embeddings.create_embeddings(texts=["foo"])

    with pytest.raises(openai.AuthenticationError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name=MOCK_EMBEDDING_MODEL_NAME,
            open_ai_dimensions=MOCK_EMBEDDING_DIMENSIONS,
            open_ai_api_version="test-api-version",
            credential=MockAzureCredential(),
            disable_batch=True,
        )
        monkeypatch.setattr(embeddings, "create_client", create_auth_error_limit_client)
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
