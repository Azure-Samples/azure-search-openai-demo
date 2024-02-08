import json

import pytest
from azure.search.documents.indexes.models import SearchField, SearchIndex
from azure.search.documents.models import (
    VectorizedQuery,
)
from openai.types.chat import ChatCompletion

from approaches.chatreadretrievereadvision import ChatReadRetrieveReadVisionApproach
from core.authentication import AuthenticationHelper


class MockOpenAIClient:
    def __init__(self):
        self.embeddings = self

    async def create(self, *args, **kwargs):
        pass


MockSearchIndex = SearchIndex(
    name="test",
    fields=[
        SearchField(name="oids", type="Collection(Edm.String)"),
        SearchField(name="groups", type="Collection(Edm.String)"),
    ],
)


@pytest.fixture
def openai_client():
    return MockOpenAIClient()


@pytest.fixture
def chat_approach(openai_client, mock_confidential_client_success):
    return ChatReadRetrieveReadVisionApproach(
        search_client=None,
        openai_client=openai_client,
        auth_helper=AuthenticationHelper(
            search_index=MockSearchIndex,
            use_authentication=True,
            server_app_id="SERVER_APP",
            server_app_secret="SERVER_SECRET",
            client_app_id="CLIENT_APP",
            tenant_id="TENANT_ID",
            require_access_control=None,
        ),
        blob_container_client=None,
        vision_endpoint="endpoint",
        vision_key="key",
        gpt4v_deployment="gpt-4v",
        gpt4v_model="gpt-4v",
        embedding_deployment="embeddings",
        embedding_model="text-",
        sourcepage_field="",
        content_field="",
        query_language="en-us",
        query_speller="lexicon",
    )


def test_build_filter(chat_approach):
    result = chat_approach.build_filter({"exclude_category": "test_category"}, {})
    assert result == "category ne 'test_category'"


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


@pytest.mark.asyncio
async def test_compute_text_embedding(chat_approach, openai_client, mock_openai_embedding):
    mock_openai_embedding(openai_client)

    result = await chat_approach.compute_text_embedding("test query")

    assert isinstance(result, VectorizedQuery)
    assert result.vector == [0.0023064255, -0.009327292, -0.0028842222]
    assert result.k_nearest_neighbors == 50
    assert result.fields == "embedding"
