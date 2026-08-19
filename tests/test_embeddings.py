import pytest

from prepdocslib.embeddings import OpenAIEmbeddings

from .test_prepdocs import MockClient, MockEmbeddingsClient


@pytest.fixture
def embeddings_client():
    return OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(None)),
        open_ai_model_name="text-embedding-ada-002",
        open_ai_dimensions=1536,
        disable_batch=False,
    )


def test_split_text_into_batches_single_batch(embeddings_client):
    texts = ["hello world", "foo bar"]
    batches = embeddings_client.split_text_into_batches(texts)
    assert len(batches) == 1
    assert batches[0].texts == texts


def test_split_text_into_batches_multiple_batches(embeddings_client):
    # Use single-token words to get predictable token counts
    # Each text needs > 4050 tokens so together they exceed the 8100 limit
    texts = ["a " * 5000, "b " * 5000]
    batches = embeddings_client.split_text_into_batches(texts)
    assert len(batches) == 2
    assert batches[0].texts == [texts[0]]
    assert batches[1].texts == [texts[1]]


def test_split_text_into_batches_respects_max_batch_size(embeddings_client):
    # max_batch_size is 16, so 17 small texts should produce 2 batches
    texts = ["hi"] * 17
    batches = embeddings_client.split_text_into_batches(texts)
    assert len(batches) == 2
    assert len(batches[0].texts) == 16
    assert len(batches[1].texts) == 1


def test_split_text_into_batches_splits_oversized_text(embeddings_client):
    """Text with more tokens than batch_token_limit should be split into smaller chunks."""
    # Create a text that exceeds the 8100 token limit
    oversized_text = "word " * 9000  # ~9000 tokens
    texts = [oversized_text]
    batches = embeddings_client.split_text_into_batches(texts)
    # Should be split into 2 chunks (8100 + remainder)
    all_texts = [t for b in batches for t in b.texts]
    assert len(all_texts) == 2
    # No batch should exceed the token limit
    for batch in batches:
        assert batch.token_length <= 8100
    # All original content should be preserved across chunks
    import tiktoken

    encoding = tiktoken.encoding_for_model("text-embedding-ada-002")
    original_tokens = encoding.encode(oversized_text)
    reconstructed_tokens = []
    for text in all_texts:
        reconstructed_tokens.extend(encoding.encode(text))
    assert len(reconstructed_tokens) == len(original_tokens)


def test_split_text_into_batches_splits_oversized_text_with_others(embeddings_client):
    """Oversized text mixed with normal texts should all be batched correctly."""
    oversized_text = "word " * 9000
    normal_text = "hello world"
    texts = [oversized_text, normal_text]
    batches = embeddings_client.split_text_into_batches(texts)
    # Oversized text splits into 2 chunks + 1 normal text = 3 texts total
    all_texts = [t for b in batches for t in b.texts]
    assert len(all_texts) == 3
    # No batch should exceed the token limit
    for batch in batches:
        assert batch.token_length <= 8100


def test_split_text_into_batches_empty(embeddings_client):
    batches = embeddings_client.split_text_into_batches([])
    assert len(batches) == 0


def test_split_text_unsupported_model():
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(None)),
        open_ai_model_name="unsupported-model",
        open_ai_dimensions=1536,
    )
    with pytest.raises(NotImplementedError):
        embeddings.split_text_into_batches(["test"])


def test_split_text_into_batches_prefixed_model():
    """OrcaRouter serves the standard OpenAI embedding models under a vendor prefix;
    batch lookups should strip the prefix so they keep working."""
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(None)),
        open_ai_model_name="openai/text-embedding-3-small",
        open_ai_dimensions=1536,
    )
    assert embeddings._base_model_name("openai/text-embedding-3-small") == "text-embedding-3-small"
    batches = embeddings.split_text_into_batches(["hello", "world"])
    assert len(batches) == 1


def test_base_model_name_unprefixed():
    """Non-vendor-prefixed model names pass through unchanged."""
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(None)),
        open_ai_model_name="text-embedding-ada-002",
        open_ai_dimensions=1536,
    )
    assert embeddings._base_model_name("text-embedding-ada-002") == "text-embedding-ada-002"


def test_compute_token_length_prefixed_model():
    embeddings = OpenAIEmbeddings(
        open_ai_client=MockClient(MockEmbeddingsClient(None)),
        open_ai_model_name="openai/text-embedding-ada-002",
        open_ai_dimensions=1536,
    )
    # The prefixed name maps back to the plain model for tiktoken.
    assert embeddings.calculate_token_length("hello world") > 0
