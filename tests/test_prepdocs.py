import openai
import pytest
import tenacity
from scripts.prepdocs import args, compute_embedding, filename_to_id


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
                "index": 0
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {
                "prompt_tokens": 8,
                "total_tokens": 8
            }
        }

    monkeypatch.setattr(openai.Embedding, "create", mock_create)
    assert compute_embedding("foo", "ada") == [
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
        compute_embedding("foo", "ada")
    captured = capsys.readouterr()
    assert captured.out.count("Rate limited on the OpenAI embeddings API") == 14


def test_compute_embedding_autherror(monkeypatch, capsys):
    monkeypatch.setattr(args, "verbose", True)
    def mock_create(*args, **kwargs):
        raise openai.error.AuthenticationError
    monkeypatch.setattr(openai.Embedding, "create", mock_create)
    monkeypatch.setattr(tenacity.nap.time, "sleep", lambda x: None)
    with pytest.raises(openai.error.AuthenticationError):
        compute_embedding("foo", "ada")
