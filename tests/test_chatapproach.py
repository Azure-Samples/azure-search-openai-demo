import json

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from openai.types.chat import ChatCompletion

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.promptmanager import PromptyManager

from .mocks import (
    MOCK_EMBEDDING_DIMENSIONS,
    MOCK_EMBEDDING_MODEL_NAME,
    MockAsyncSearchResultsIterator,
)


async def mock_search(*args, **kwargs):
    return MockAsyncSearchResultsIterator(kwargs.get("search_text"), kwargs.get("vector_queries"))


@pytest.fixture
def chat_approach():
    return ChatReadRetrieveReadApproach(
        search_client=None,
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
        prompt_manager=PromptyManager(),
    )


def test_get_search_query(chat_approach):
    payload = """
    {
	"id": "chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM",
	"object": "chat.completion",
	"created": 1695324963,
	"model": "gpt-35-turbo",
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
    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-35-turbo","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"content":"","role":"assistant"},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
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
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
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


async def test_search_results_query_rewriting(monkeypatch):
    chat_approach = ChatReadRetrieveReadApproach(
        search_client=SearchClient(endpoint="", index_name="", credential=AzureKeyCredential("")),
        auth_helper=None,
        openai_client=None,
        chatgpt_model="gpt-35-turbo",
        chatgpt_deployment="chat",
        embedding_deployment="embeddings",
        embedding_model=MOCK_EMBEDDING_MODEL_NAME,
        embedding_dimensions=MOCK_EMBEDDING_DIMENSIONS,
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
        return mock_search(*args, **kwargs)

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
        use_query_rewrites=True,
    )
    assert len(results) == 1
    assert query_rewrites == "generative"
