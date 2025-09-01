import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentAzureSearchDocReference,
    KnowledgeAgentMessage,
    KnowledgeAgentRetrievalResponse,
)
from azure.search.documents.aio import SearchClient

from .conftest import create_mock_retrieve
from .mocks import (
    MockAsyncSearchResultsIterator,
)


@pytest.mark.asyncio
async def test_agentic_retrieval_non_hydrated_default_sort(chat_approach, monkeypatch):
    """Test non-hydrated path with default sorting (preserve original order)"""

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
async def test_agentic_retrieval_non_hydrated_interleaved_sort(chat_approach, monkeypatch):
    """Test non-hydrated path with interleaved sorting"""

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
async def test_agentic_retrieval_hydrated_with_sorting(chat_approach_with_hydration, monkeypatch):
    """Test hydrated path with sorting"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    async def mock_search(self, *args, **kwargs):
        # For hydration, we expect a filter like "search.in(id, 'doc1,doc2', ',')"
        return MockAsyncSearchResultsIterator("hydrated_multi", None)

    monkeypatch.setattr(SearchClient, "search", mock_search)

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        results_merge_strategy="interleaved",
    )

    assert len(results) == 2
    # Should have hydrated content, not source_data content
    assert results[0].content == "Hydrated content 1"
    assert results[1].content == "Hydrated content 2"
    # Should still have agent queries injected
    assert results[0].search_agent_query == "first query"
    assert results[1].search_agent_query == "second query"


@pytest.mark.asyncio
async def test_hydrate_agent_references_deduplication(chat_approach_with_hydration, monkeypatch):
    """Test that hydrate_agent_references deduplicates doc_keys"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("duplicates"))

    async def mock_search(self, *args, **kwargs):
        # For deduplication test, we expect doc1 and doc2 to be in the filter
        return MockAsyncSearchResultsIterator("hydrated_multi", None)

    monkeypatch.setattr(SearchClient, "search", mock_search)

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    # Should only get 2 unique documents despite 3 references (doc1 appears twice)
    assert len(results) == 2
    doc_ids = [doc.id for doc in results]
    assert "doc1" in doc_ids
    assert "doc2" in doc_ids


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
async def test_activity_mapping_injection(chat_approach, monkeypatch):
    """Test that search_agent_query is properly injected from activity mapping"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("sorting"))

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    # Verify that search_agent_query is correctly mapped from activity
    assert len(results) == 2

    # Find each document and verify its query
    doc1 = next(doc for doc in results if doc.id == "doc1")
    doc2 = next(doc for doc in results if doc.id == "doc2")

    assert doc1.search_agent_query == "first query"  # From activity_source=1
    assert doc2.search_agent_query == "second query"  # From activity_source=2


@pytest.mark.asyncio
async def test_hydrate_agent_references_missing_doc_keys(chat_approach_with_hydration, monkeypatch):
    """Test that hydrate_agent_references handles missing/empty doc_keys correctly"""

    monkeypatch.setattr(
        KnowledgeAgentRetrievalClient,
        "retrieve",
        create_mock_retrieve("missing_doc_key"),
    )

    async def mock_search(self, *args, **kwargs):
        return MockAsyncSearchResultsIterator("hydrated_single", None)

    monkeypatch.setattr(SearchClient, "search", mock_search)

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    # Should only get doc3 since doc_key was missing/empty for others
    assert len(results) == 1
    assert results[0].id == "doc1"  # From mock search result
    assert results[0].content == "Hydrated content 1"


@pytest.mark.asyncio
async def test_hydrate_agent_references_empty_doc_keys(chat_approach_with_hydration, monkeypatch):
    """Test that hydrate_agent_references handles case with no valid doc_keys"""

    async def mock_retrieval_no_valid_keys(*args, **kwargs):
        return KnowledgeAgentRetrievalResponse(
            response=[KnowledgeAgentMessage(role="assistant", content=[])],
            activity=[],
            references=[
                KnowledgeAgentAzureSearchDocReference(
                    id="1",
                    activity_source=1,
                    doc_key=None,  # No valid doc_key
                    source_data={"content": "Content 1", "sourcepage": "page1.pdf"},
                ),
            ],
        )

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", mock_retrieval_no_valid_keys)
    # No need to mock search since it should never be called

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    # Should get empty results since no valid doc_keys
    assert len(results) == 0


@pytest.mark.asyncio
async def test_hydrate_agent_references_search_returns_empty(chat_approach_with_hydration, monkeypatch):
    """Test that hydrate_agent_references handles case where search returns no results"""

    async def mock_retrieval_valid_keys(*args, **kwargs):
        return KnowledgeAgentRetrievalResponse(
            response=[KnowledgeAgentMessage(role="assistant", content=[])],
            activity=[],
            references=[
                KnowledgeAgentAzureSearchDocReference(
                    id="1",
                    activity_source=1,
                    doc_key="nonexistent_doc",  # Valid doc_key but document doesn't exist
                    source_data={"content": "Content 1", "sourcepage": "page1.pdf"},
                ),
            ],
        )

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", mock_retrieval_valid_keys)

    async def mock_search(self, *args, **kwargs):
        return MockAsyncSearchResultsIterator("hydrated_empty", None)

    monkeypatch.setattr(SearchClient, "search", mock_search)

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name="test-index"
    )

    # When hydration is enabled but returns empty results, we should get empty list
    # rather than falling back to source_data (this is the expected behavior)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_agentic_retrieval_with_top_limit_during_building(chat_approach, monkeypatch):
    """Test that document building respects top limit and breaks early (non-hydrated path)"""

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


@pytest.mark.asyncio
async def test_hydrate_agent_references_with_top_limit_during_collection(chat_approach_with_hydration, monkeypatch):
    """Test that hydration respects top limit when collecting doc_keys"""

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", create_mock_retrieve("top_limit"))

    async def mock_search(self, *args, **kwargs):
        return MockAsyncSearchResultsIterator("hydrated_multi", None)

    monkeypatch.setattr(SearchClient, "search", mock_search)

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[],
        agent_client=agent_client,
        search_index_name="test-index",
        top=2,  # Limit to 2 documents
    )

    # Should get exactly 2 documents due to top limit during doc_keys collection
    assert len(results) == 2
    assert results[0].content == "Hydrated content 1"
    assert results[1].content == "Hydrated content 2"
