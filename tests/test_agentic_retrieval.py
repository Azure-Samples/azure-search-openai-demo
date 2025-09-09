"""Agentic retrieval tests"""

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentMessage,
    KnowledgeAgentRetrievalResponse,
)

from .conftest import create_mock_retrieve


@pytest.mark.asyncio
async def test_agentic_retrieval_default_sort(chat_approach, monkeypatch):
    """Test default sorting (preserve original order)"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        results_merge_strategy=None,  # Default sorting
    )

    assert len(results) == 2
    # Default sorting preserves original order (doc2, doc1)
    assert results[0].id == "doc2"
    assert results[0].content == "Content 2"
    assert results[0].search_agent_query == "second query"

    assert results[1].id == "doc1"
    assert results[1].content == "Content 1"
    assert results[1].search_agent_query == "first query"


@pytest.mark.asyncio
async def test_agentic_retrieval_interleaved_sort(chat_approach, monkeypatch):
    """Test interleaved sorting"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        results_merge_strategy="interleaved",
    )

    assert len(results) == 2
    # Interleaved sorting orders by reference ID (1, 2)
    assert results[0].id == "doc1"  # ref.id = "1"
    assert results[0].content == "Content 1"
    assert results[0].search_agent_query == "first query"

    assert results[1].id == "doc2"  # ref.id = "2"
    assert results[1].content == "Content 2"
    assert results[1].search_agent_query == "second query"


@pytest.mark.asyncio
async def test_agentic_retrieval_no_references(chat_approach, monkeypatch):
    """Test behavior when agent returns no references"""

    async def mock_retrieval(*args, **kwargs):
        return KnowledgeAgentRetrievalResponse(
            response=[KnowledgeAgentMessage(role="assistant", content=[])],
            activity=[],
            references=[],
        )

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", mock_retrieval)

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    assert len(results) == 0


@pytest.mark.asyncio
async def test_agentic_retrieval_with_top_limit_during_building(chat_approach, monkeypatch):
    """Test that document building respects top limit and breaks early"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("top_limit"))

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        top=5,  # Limit to 5 documents
    )

    # Should get exactly 5 documents due to top limit during building
    assert len(results) == 5
    for i, result in enumerate(results):
        assert result.id == f"doc{i}"
        assert result.content == f"Content {i}"
