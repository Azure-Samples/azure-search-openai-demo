import json

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai.types.chat import ChatCompletion

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.promptmanager import PromptyManager
from prepdocslib.embeddings import ImageEmbeddings

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
    MockAsyncSearchResultsIterator,
    mock_retrieval_response,
)


async def mock_search(*args, **kwargs):
    return MockAsyncSearchResultsIterator(kwargs.get("search_text"), kwargs.get("vector_queries"))


async def mock_retrieval(*args, **kwargs):
    return mock_retrieval_response()


def test_get_search_query(chat_approach):
    payload = """
    {
	"id": "chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM",
	"object": "chat.completion",
	"created": 1695324963,
	"model": "gpt-4.1-mini",
	"prompt_filter_results": [
		{
			"prompt_index": 0,
			"content_filter_results": {
				"hate": {
					"filtered": false,
					"severity": "safe"
				},
				"self_harm": {
					"filtered": false,
					"severity": "safe"
				},
				"sexual": {
					"filtered": false,
					"severity": "safe"
				},
				"violence": {
					"filtered": false,
					"severity": "safe"
				}
			}
		}
	],
	"choices": [
		{
			"index": 0,
			"finish_reason": "function_call",
			"message": {
				"content": "this is the query",
				"role": "assistant",
				"tool_calls": [
					{
                        "id": "search_sources1235",
						"type": "function",
						"function": {
							"name": "search_sources",
							"arguments": "{\\n\\"search_query\\":\\"accesstelemedicineservices\\"\\n}"
						}
					}
				]
			},
			"content_filter_results": {

			}
		}
	],
	"usage": {
		"completion_tokens": 19,
		"prompt_tokens": 425,
		"total_tokens": 444
	}
}
"""
    default_query = "hello"
    chatcompletions = ChatCompletion.model_validate(json.loads(payload), strict=False)
    query = chat_approach.get_search_query(chatcompletions, default_query)

    assert query == "accesstelemedicineservices"


def test_get_search_query_returns_default(chat_approach):
    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-4.1-mini","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"content":"","role":"assistant"},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
    default_query = "hello"
    chatcompletions = ChatCompletion.model_validate(json.loads(payload), strict=False)
    query = chat_approach.get_search_query(chatcompletions, default_query)

    assert query == default_query


def test_extract_followup_questions(chat_approach):
    content = "Here is answer to your question.<<What is the dress code?>>"
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == "Here is answer to your question."
    assert followup_questions == ["What is the dress code?"]


def test_extract_followup_questions_three(chat_approach):
    content = """Here is answer to your question.

<<What are some examples of successful product launches they should have experience with?>>
<<Are there any specific technical skills or certifications required for the role?>>
<<Is there a preference for candidates with experience in a specific industry or sector?>>"""
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == "Here is answer to your question.\n\n"
    assert followup_questions == [
        "What are some examples of successful product launches they should have experience with?",
        "Are there any specific technical skills or certifications required for the role?",
        "Is there a preference for candidates with experience in a specific industry or sector?",
    ]


def test_extract_followup_questions_no_followup(chat_approach):
    content = "Here is answer to your question."
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == "Here is answer to your question."
    assert followup_questions == []


def test_extract_followup_questions_no_pre_content(chat_approach):
    content = "<<What is the dress code?>>"
    pre_content, followup_questions = chat_approach.extract_followup_questions(content)
    assert pre_content == ""
    assert followup_questions == ["What is the dress code?"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "minimum_search_score,minimum_reranker_score,expected_result_count",
    [
        (0, 0, 1),
        (0, 2, 1),
        (0.03, 0, 1),
        (0.03, 2, 1),
        (1, 0, 0),
        (0, 4, 0),
        (1, 4, 0),
    ],
)
async def test_search_results_filtering_by_scores(
    monkeypatch, minimum_search_score, minimum_reranker_score, expected_result_count
):

    chat_approach = ChatReadRetrieveReadApproach(
        search_client=SearchClient(endpoint="", index_name="", credential=AzureKeyCredential("")),
        search_index_name=None,
        agent_model=None,
        agent_deployment=None,
        agent_client=None,
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-4.1-mini",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        embedding_field="embedding3",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
        prompt_manager=PromptyManager(),
    )

    monkeypatch.setattr(SearchClient, "search", mock_search)

    filtered_results = await chat_approach.search(
        top=10,
        query_text="test query",
        filter=None,
        vectors=[],
        use_text_search=True,
        use_vector_search=True,
        use_semantic_ranker=True,
        use_semantic_captions=True,
        minimum_search_score=minimum_search_score,
        minimum_reranker_score=minimum_reranker_score,
    )

    assert (
        len(filtered_results) == expected_result_count
    ), f"Expected {expected_result_count} results with minimum_search_score={minimum_search_score} and minimum_reranker_score={minimum_reranker_score}"


@pytest.mark.asyncio
async def test_search_results_query_rewriting(monkeypatch):
    chat_approach = ChatReadRetrieveReadApproach(
        search_client=SearchClient(endpoint="", index_name="", credential=AzureKeyCredential("")),
        search_index_name=None,
        agent_model=None,
        agent_deployment=None,
        agent_client=None,
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        embedding_field="embedding3",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
        prompt_manager=PromptyManager(),
    )

    query_rewrites = None

    async def validate_qr_and_mock_search(*args, **kwargs):
        nonlocal query_rewrites
        query_rewrites = kwargs.get("query_rewrites")
        return await mock_search(*args, **kwargs)

    monkeypatch.setattr(SearchClient, "search", validate_qr_and_mock_search)

    results = await chat_approach.search(
        top=10,
        query_text="test query",
        filter=None,
        vectors=[],
        use_text_search=True,
        use_vector_search=True,
        use_semantic_ranker=True,
        use_semantic_captions=True,
        use_query_rewriting=True,
    )
    assert len(results) == 1
    assert query_rewrites == "generative"


@pytest.mark.asyncio
async def test_agent_retrieval_results(monkeypatch):
    chat_approach = ChatReadRetrieveReadApproach(
        search_client=None,
        search_index_name=None,
        agent_model=None,
        agent_deployment=None,
        agent_client=None,
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        embedding_field="embedding3",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
        prompt_manager=PromptyManager(),
    )

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", mock_retrieval)

    _, results = await chat_approach.run_agentic_retrieval(messages=[], agent_client=agent_client, search_index_name="")

    assert len(results) == 1
    assert results[0].id == "Benefit_Options-2.pdf"
    assert results[0].content == "There is a whistleblower policy."
    assert results[0].sourcepage == "Benefit_Options-2.pdf"
    assert results[0].search_agent_query == "whistleblower query"


@pytest.mark.asyncio
async def test_agentic_retrieval_without_hydration(chat_approach, monkeypatch):
    """Test agentic retrieval without hydration"""

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", mock_retrieval)

    _, results = await chat_approach.run_agentic_retrieval(messages=[], agent_client=agent_client, search_index_name="")

    assert len(results) == 1
    assert results[0].id == "Benefit_Options-2.pdf"
    # Content should be from source_data since no hydration
    assert results[0].content == "There is a whistleblower policy."
    assert results[0].sourcepage == "Benefit_Options-2.pdf"
    assert results[0].search_agent_query == "whistleblower query"
    # These fields should NOT be present without hydration
    assert not hasattr(results[0], "sourcefile") or results[0].sourcefile is None
    assert not hasattr(results[0], "category") or results[0].category is None
    assert not hasattr(results[0], "score") or results[0].score is None


async def mock_search_with_hydration(*args, **kwargs):
    """Mock search client that returns data with sourcefile and category for hydration testing"""
    return MockAsyncSearchResultsIterator("hydrated", None)


@pytest.mark.asyncio
async def test_agentic_retrieval_with_hydration(chat_approach_with_hydration, monkeypatch):
    """Test agentic retrieval with hydration enabled"""

    agent_client = KnowledgeAgentRetrievalClient(endpoint="", agent_name="", credential=AzureKeyCredential(""))

    # Mock the agent retrieval and search client
    monkeypatch.setattr(KnowledgeAgentRetrievalClient, "retrieve", mock_retrieval)
    monkeypatch.setattr(SearchClient, "search", mock_search_with_hydration)

    _, results = await chat_approach_with_hydration.run_agentic_retrieval(
        messages=[], agent_client=agent_client, search_index_name=""
    )

    assert len(results) == 1
    assert results[0].id == "Benefit_Options-2.pdf"
    # Content should be from hydrated search, not source_data
    assert results[0].content == "There is a whistleblower policy."
    assert results[0].sourcepage == "Benefit_Options-2.pdf"
    assert results[0].search_agent_query == "whistleblower query"
    # These fields should be present from hydration (from search results)
    assert results[0].sourcefile == "Benefit_Options.pdf"
    assert results[0].category == "benefits"
    assert results[0].score == 0.03279569745063782
    assert results[0].reranker_score == 3.4577205181121826


@pytest.mark.asyncio
async def test_compute_multimodal_embedding(monkeypatch, chat_approach):
    # Create a mock for the ImageEmbeddings.create_embedding_for_text method
    async def mock_create_embedding_for_text(self, q: str):
        # Return a mock vector
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    monkeypatch.setattr(ImageEmbeddings, "create_embedding_for_text", mock_create_embedding_for_text)

    # Create a mock ImageEmbeddings instance and set it on the chat_approach
    mock_image_embeddings = ImageEmbeddings(endpoint="https://mock-endpoint", token_provider=lambda: None)
    chat_approach.image_embeddings_client = mock_image_embeddings

    # Test the compute_multimodal_embedding method
    query = "What's in this image?"
    result = await chat_approach.compute_multimodal_embedding(query)

    # Verify the result is a VectorizedQuery with the expected properties
    assert isinstance(result, VectorizedQuery)
    assert result.vector == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert result.k_nearest_neighbors == 50
    assert result.fields == "images/embedding"


@pytest.mark.asyncio
async def test_compute_multimodal_embedding_no_client():
    """Test that compute_multimodal_embedding raises ValueError when image_embeddings_client is not set."""
    # Create a chat approach without an image_embeddings_client
    chat_approach = ChatReadRetrieveReadApproach(
        search_client=SearchClient(endpoint="", index_name="", credential=AzureKeyCredential("")),
        search_index_name=None,
        agent_model=None,
        agent_deployment=None,
        agent_client=None,
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        embedding_field="embedding3",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
        prompt_manager=PromptyManager(),
        # Explicitly set image_embeddings_client to None
        image_embeddings_client=None,
    )

    # Test that calling compute_multimodal_embedding raises a ValueError
    with pytest.raises(ValueError, match="Approach is missing an image embeddings client for multimodal queries"):
        await chat_approach.compute_multimodal_embedding("What's in this image?")
