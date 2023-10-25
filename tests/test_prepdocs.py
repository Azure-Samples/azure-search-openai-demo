import io

import openai
import pytest
import tenacity
from conftest import MockAzureCredential
from scripts.prepdocs.files import (
    ADLSGen2ListFileStrategy,
    AzureOpenAIEmbeddingService,
    File,
    OpenAIEmbeddingService,
)


def test_filename_to_id():
    empty = io.BytesIO()
    empty.name = "foo.pdf"
    # test ascii filename
    assert File(empty).filename_to_id() == "file-foo_pdf-666F6F2E706466"
    # test filename containing unicode
    empty.name = "foo\u00A9.txt"
    assert File(empty).filename_to_id() == "file-foo__txt-666F6FC2A92E747874"
    # test filenaming starting with unicode
    empty.name = "ファイル名.pdf"
    assert File(empty).filename_to_id() == "file-______pdf-E38395E382A1E382A4E383ABE5908D2E706466"


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


@pytest.mark.asyncio
async def test_read_adls_gen2_files(monkeypatch, mock_data_lake_service_client):
    def mock_remove(*args, **kwargs):
        pass

    adlsgen2_list_strategy = ADLSGen2ListFileStrategy(
        data_lake_storage_account="a", data_lake_filesystem="a", data_lake_path="a", credential=MockAzureCredential()
    )

    files = [file async for file in adlsgen2_list_strategy.list()]
    assert len(files) == 3
    print(files[0].content.name)

    class MockIndexSections:
        def __init__(self):
            self.filenames = []

        def call(self, filename, sections, acls):
            if filename == "a.txt":
                assert acls == {"oids": ["A-USER-ID"], "groups": ["A-GROUP-ID"]}
            elif filename == "b.txt":
                assert acls == {"oids": ["B-USER-ID"], "groups": ["B-GROUP-ID"]}
            elif filename == "c.txt":
                assert acls == {"oids": ["C-USER-ID"], "groups": ["C-GROUP-ID"]}
            else:
                raise Exception(f"Unexpected filename {filename}")

            self.filenames.append(filename)

    mock_index_sections = MockIndexSections()

    def mock_index_sections_method(filename, sections, acls):
        mock_index_sections.call(filename, sections, acls)

    # read_adls_gen2_files(use_vectors=True, vectors_batch_support=True)

    # assert mock_index_sections.filenames == ["a.txt", "b.txt", "c.txt"]
