"""Agentic retrieval tests"""

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.knowledgebases.aio import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseRetrievalResponse,
)
from openai.types.chat import ChatCompletion

from approaches.approach import RewriteQueryResult

from .conftest import create_mock_retrieve


@pytest.mark.asyncio
async def test_agentic_retrieval_default_sort(chat_approach, monkeypatch):
    """Test default sorting (preserve original order)"""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    knowledgebase_client = KnowledgeBaseRetrievalClient(
        endpoint="", knowledge_base_name="", credential=AzureKeyCredential("")
    )

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[], knowledgebase_client=knowledgebase_client, search_index_name="test-index"
    )

    assert len(agentic_results.documents) == 2
    assert agentic_results.web_results == []
    # Default sorting preserves original order (doc2, doc1)
    assert agentic_results.documents[0].id == "doc2"
    assert agentic_results.documents[0].content == "Content 2"
    assert agentic_results.documents[0].activity.query == "second query"

    assert agentic_results.documents[1].id == "doc1"
    assert agentic_results.documents[1].content == "Content 1"
    assert agentic_results.documents[1].activity.query == "first query"


@pytest.mark.asyncio
async def test_agentic_retrieval_no_references(chat_approach, monkeypatch):
    """Test behavior when agent returns no references"""

    async def mock_retrieval(*args, **kwargs):
        return KnowledgeBaseRetrievalResponse(
            response=[KnowledgeBaseMessage(role="assistant", content=[])],
            activity=[],
            references=[],
        )

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", mock_retrieval)

    knowledgebase_client = KnowledgeBaseRetrievalClient(
        endpoint="", knowledge_base_name="", credential=AzureKeyCredential("")
    )

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[], knowledgebase_client=knowledgebase_client, search_index_name="test-index"
    )

    assert len(agentic_results.documents) == 0
    assert agentic_results.web_results == []


@pytest.mark.asyncio
async def test_agentic_retrieval_web_results(chat_approach, monkeypatch):
    """Ensure web references are returned separately and serialized into data points"""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("web"))

    knowledgebase_client = KnowledgeBaseRetrievalClient(
        endpoint="", knowledge_base_name="", credential=AzureKeyCredential("")
    )

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[], knowledgebase_client=knowledgebase_client, search_index_name="test-index"
    )

    assert len(agentic_results.documents) == 1
    assert len(agentic_results.web_results) == 1
    assert agentic_results.web_results[0].url == "https://contoso.example"

    data_points = await chat_approach.get_sources_content(
        agentic_results.documents,
        use_semantic_captions=False,
        include_text_sources=True,
        download_image_sources=False,
        web_results=agentic_results.web_results,
    )

    assert data_points.external_results_metadata is not None
    assert data_points.external_results_metadata[0]["url"] == "https://contoso.example"
    assert "https://contoso.example" in data_points.citations


@pytest.mark.asyncio
async def test_agentic_retrieval_sharepoint_results(chat_approach, monkeypatch):
    """SharePoint references should be captured and exposed alongside documents."""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("sharepoint"))

    knowledgebase_client = KnowledgeBaseRetrievalClient(
        endpoint="", knowledge_base_name="", credential=AzureKeyCredential("")
    )

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[],
        knowledgebase_client=knowledgebase_client,
        search_index_name="test-index",
        use_sharepoint_source=True,
    )

    assert len(agentic_results.sharepoint_results) == 1
    sharepoint_entry = agentic_results.sharepoint_results[0]
    assert sharepoint_entry.web_url == "https://contoso.sharepoint.com/sites/hr/document"

    # Verify SharePoint results are captured
    assert sharepoint_entry.title == "SharePoint Title"
    assert sharepoint_entry.content == "SharePoint content"


@pytest.mark.asyncio
async def test_agentic_retrieval_minimal_uses_query_rewrite(chat_approach, monkeypatch):
    """Minimal reasoning effort should invoke query rewriting and surface the rewrite result."""

    completion_payload = {
        "id": "rewrite-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4.1-mini",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Rewritten"},
            }
        ],
        "usage": {"completion_tokens": 1, "prompt_tokens": 1, "total_tokens": 2},
    }
    rewrite_completion = ChatCompletion.model_validate(completion_payload, strict=False)

    rewrite_result = RewriteQueryResult(
        query="rewritten query",
        messages=[{"role": "user", "content": "Original"}],
        completion=rewrite_completion,
        reasoning_effort="minimal",
    )

    async def fake_rewrite_query(**_kwargs):
        return rewrite_result

    monkeypatch.setattr(chat_approach, "rewrite_query", fake_rewrite_query)
    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("web"))

    knowledgebase_client = KnowledgeBaseRetrievalClient(
        endpoint="", knowledge_base_name="", credential=AzureKeyCredential("")
    )

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[{"role": "user", "content": "Original"}],
        knowledgebase_client=knowledgebase_client,
        search_index_name="test-index",
        retrieval_reasoning_effort="minimal",
    )

    assert agentic_results.rewrite_result is not None
    assert agentic_results.rewrite_result.query == "rewritten query"


@pytest.mark.asyncio
async def test_agentic_retrieval_minimal_requires_string(chat_approach):
    """When minimal reasoning is requested the latest message must be a string."""

    knowledgebase_client = KnowledgeBaseRetrievalClient(
        endpoint="", knowledge_base_name="", credential=AzureKeyCredential("")
    )

    with pytest.raises(ValueError, match="most recent message content must be a string"):
        await chat_approach.run_agentic_retrieval(
            messages=[{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            knowledgebase_client=knowledgebase_client,
            search_index_name="test-index",
            retrieval_reasoning_effort="minimal",
        )
