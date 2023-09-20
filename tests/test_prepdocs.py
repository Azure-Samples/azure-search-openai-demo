import openai
import pytest
import scripts
import tenacity
from conftest import MockAzureCredential
from scripts.prepdocs import (
    args,
    compute_embedding,
    filename_to_id,
    read_adls_gen2_files,
)


def test_filename_to_id():
    # test ascii filename
    assert filename_to_id("foo.pdf") == "file-foo_pdf-666F6F2E706466"
    # test filename containing unicode
    assert filename_to_id("foo\u00A9.txt") == "file-foo__txt-666F6FC2A92E747874"
    # test filenaming starting with unicode
    assert filename_to_id("ファイル名.pdf") == "file-______pdf-E38395E382A1E382A4E383ABE5908D2E706466"


def test_compute_embedding_success(monkeypatch, capsys):
    monkeypatch.setattr(args, "verbose", True)

    def mock_create(*args, **kwargs):
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

    monkeypatch.setattr(openai.Embedding, "create", mock_create)
    assert compute_embedding("foo", "ada", "text-ada-003") == [
        0.0023064255,
        -0.009327292,
        -0.0028842222,
    ]


def test_compute_embedding_ratelimiterror(monkeypatch, capsys):
    monkeypatch.setattr(args, "verbose", True)

    def mock_create(*args, **kwargs):
        raise openai.error.RateLimitError

    monkeypatch.setattr(openai.Embedding, "create", mock_create)
    monkeypatch.setattr(tenacity.nap.time, "sleep", lambda x: None)
    with pytest.raises(tenacity.RetryError):
        compute_embedding("foo", "ada", "text-ada-003")
    captured = capsys.readouterr()
    assert captured.out.count("Rate limited on the OpenAI embeddings API") == 14


def test_compute_embedding_autherror(monkeypatch, capsys):
    monkeypatch.setattr(args, "verbose", True)

    def mock_create(*args, **kwargs):
        raise openai.error.AuthenticationError

    monkeypatch.setattr(openai.Embedding, "create", mock_create)
    monkeypatch.setattr(tenacity.nap.time, "sleep", lambda x: None)
    with pytest.raises(openai.error.AuthenticationError):
        compute_embedding("foo", "ada", "text-ada-003")


def test_read_adls_gen2_files(monkeypatch, mock_data_lake_service_client):
    monkeypatch.setattr(args, "verbose", True)
    monkeypatch.setattr(args, "useacls", True)
    monkeypatch.setattr(args, "datalakestorageaccount", "STORAGE")
    monkeypatch.setattr(scripts.prepdocs, "adls_gen2_creds", MockAzureCredential())

    def mock_remove(*args, **kwargs):
        pass

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

    monkeypatch.setattr(scripts.prepdocs, "remove_blobs", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "upload_blobs", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "remove_from_index", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "get_document_text", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "update_embeddings_in_batch", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "create_sections", mock_remove)
    monkeypatch.setattr(scripts.prepdocs, "index_sections", mock_index_sections_method)

    read_adls_gen2_files(use_vectors=True, vectors_batch_support=True)

    assert mock_index_sections.filenames == ["a.txt", "b.txt", "c.txt"]
