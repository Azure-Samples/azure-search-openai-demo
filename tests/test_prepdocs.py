import openai
import pytest
import tenacity
from conftest import MockAzureCredential

from scripts.prepdocslib.embeddings import (
    AzureOpenAIEmbeddingService,
    OpenAIEmbeddingService,
)


@pytest.mark.asyncio
async def test_compute_embedding_success(monkeypatch):
    async def mock_create(*args, **kwargs):
        # From https://platform.openai.com/docs/api-reference/embeddings/create
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [
                        0.0023064255,
                        -0.009327292,
                        -0.0028842222,
                    ],
                    "index": 0,
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        }

    monkeypatch.setattr(openai.Embedding, "acreate", mock_create)
    embeddings = AzureOpenAIEmbeddingService(
        open_ai_service="x",
        open_ai_deployment="x",
        open_ai_model_name="text-ada-003",
        credential=MockAzureCredential(),
        disable_batch=False,
    )
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
        open_ai_model_name="text-ada-003",
        credential=MockAzureCredential(),
        disable_batch=True,
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddingService(
        open_ai_model_name="text-ada-003", credential=MockAzureCredential(), organization="org", disable_batch=False
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]

    embeddings = OpenAIEmbeddingService(
        open_ai_model_name="text-ada-003", credential=MockAzureCredential(), organization="org", disable_batch=True
    )
    assert await embeddings.create_embeddings(texts=["foo"]) == [
        [
            0.0023064255,
            -0.009327292,
            -0.0028842222,
        ]
    ]


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_batch(monkeypatch, capsys):
    async def mock_acreate(*args, **kwargs):
        raise openai.error.RateLimitError

    monkeypatch.setattr(openai.Embedding, "acreate", mock_acreate)
    monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
    with pytest.raises(tenacity.RetryError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name="text-embedding-ada-002",
            credential=MockAzureCredential(),
            disable_batch=False,
            verbose=True,
        )
        await embeddings.create_embeddings(texts=["foo"])
    captured = capsys.readouterr()
    assert captured.out.count("Rate limited on the OpenAI embeddings API") == 14


@pytest.mark.asyncio
async def test_compute_embedding_ratelimiterror_single(monkeypatch, capsys):
    async def mock_acreate(*args, **kwargs):
        raise openai.error.RateLimitError

    monkeypatch.setattr(openai.Embedding, "acreate", mock_acreate)
    monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
    with pytest.raises(tenacity.RetryError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name="text-embedding-ada-002",
            credential=MockAzureCredential(),
            disable_batch=True,
            verbose=True,
        )
        await embeddings.create_embeddings(texts=["foo"])
    captured = capsys.readouterr()
    assert captured.out.count("Rate limited on the OpenAI embeddings API") == 14


@pytest.mark.asyncio
async def test_compute_embedding_autherror(monkeypatch, capsys):
    async def mock_acreate(*args, **kwargs):
        raise openai.error.AuthenticationError

    monkeypatch.setattr(openai.Embedding, "acreate", mock_acreate)
    monkeypatch.setattr(tenacity.wait_random_exponential, "__call__", lambda x, y: 0)
    with pytest.raises(openai.error.AuthenticationError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name="text-embedding-ada-002",
            credential=MockAzureCredential(),
            disable_batch=False,
            verbose=True,
        )
        await embeddings.create_embeddings(texts=["foo"])

    with pytest.raises(openai.error.AuthenticationError):
        embeddings = AzureOpenAIEmbeddingService(
            open_ai_service="x",
            open_ai_deployment="x",
            open_ai_model_name="text-embedding-ada-002",
            credential=MockAzureCredential(),
            disable_batch=True,
            verbose=True,
        )
        await embeddings.create_embeddings(texts=["foo"])
