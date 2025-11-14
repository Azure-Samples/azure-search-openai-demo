"""Agentic retrieval tests"""

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.knowledgebases.aio import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseRetrievalResponse,
)

from .conftest import create_mock_retrieve


@pytest.mark.asyncio
async def test_agentic_retrieval_default_sort(chat_approach, monkeypatch):
    """Test default sorting (preserve original order)"""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    agent_client = KnowledgeBaseRetrievalClient(endpoint="", knowledge_base_name="", credential=AzureKeyCredential(""))

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        results_merge_strategy=None,  # Default sorting
    )

    assert len(agentic_results.documents) == 2
    assert agentic_results.web_results == []
    # Default sorting preserves original order (doc2, doc1)
    assert agentic_results.documents[0].id == "doc2"
    assert agentic_results.documents[0].content == "Content 2"
    assert agentic_results.documents[0].search_agent_query == "second query"

    assert agentic_results.documents[1].id == "doc1"
    assert agentic_results.documents[1].content == "Content 1"
    assert agentic_results.documents[1].search_agent_query == "first query"


@pytest.mark.asyncio
async def test_agentic_retrieval_interleaved_sort(chat_approach, monkeypatch):
    """Test interleaved sorting"""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    agent_client = KnowledgeBaseRetrievalClient(endpoint="", knowledge_base_name="", credential=AzureKeyCredential(""))

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        results_merge_strategy="interleaved",
    )

    assert len(agentic_results.documents) == 2
    assert agentic_results.web_results == []
    # Interleaved sorting orders by reference ID (1, 2)
    assert agentic_results.documents[0].id == "doc1"  # ref.id = "1"
    assert agentic_results.documents[0].content == "Content 1"
    assert agentic_results.documents[0].search_agent_query == "first query"

    assert agentic_results.documents[1].id == "doc2"  # ref.id = "2"
    assert agentic_results.documents[1].content == "Content 2"
    assert agentic_results.documents[1].search_agent_query == "second query"


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

    agent_client = KnowledgeBaseRetrievalClient(endpoint="", knowledge_base_name="", credential=AzureKeyCredential(""))

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    assert len(agentic_results.documents) == 0
    assert agentic_results.web_results == []


@pytest.mark.asyncio
async def test_agentic_retrieval_with_top_limit_during_building(chat_approach, monkeypatch):
    """Test that document building respects top limit and breaks early"""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("top_limit"))

    agent_client = KnowledgeBaseRetrievalClient(endpoint="", knowledge_base_name="", credential=AzureKeyCredential(""))

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        top=5,  # Limit to 5 documents
    )

    # Should get exactly 5 documents due to top limit during building
    assert len(agentic_results.documents) == 5
    for i, result in enumerate(agentic_results.documents):
        assert result.id == f"doc{i}"
        assert result.content == f"Content {i}"
    assert agentic_results.web_results == []


@pytest.mark.asyncio
async def test_agentic_retrieval_web_results(chat_approach, monkeypatch):
    """Ensure web references are returned separately and serialized into data points"""

    monkeypatch.setattr(KnowledgeBaseRetrievalClient, "retrieve", create_mock_retrieve("web"))

    agent_client = KnowledgeBaseRetrievalClient(endpoint="", knowledge_base_name="", credential=AzureKeyCredential(""))

    agentic_results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        results_merge_strategy="interleaved",
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

    assert data_points.web is not None
    assert data_points.web[0]["url"] == "https://contoso.example"
    assert "https://contoso.example" in data_points.citations
