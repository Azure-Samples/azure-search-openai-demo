import json

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach


def test_get_search_query():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-35-turbo","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"role":"assistant","function_call":{"name":"search_sources","arguments":"{\\n\\"search_query\\":\\"accesstelemedicineservices\\"\\n}"}},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
    default_query = "hello"
    query = chat_approach.get_search_query(json.loads(payload), default_query)

    assert query == "accesstelemedicineservices"


def test_get_search_query_returns_default():
    chat_approach = ChatReadRetrieveReadApproach(None, "", "gpt-35-turbo", "gpt-35-turbo", "", "", "", "")

    payload = '{"id":"chatcmpl-81JkxYqYppUkPtOAia40gki2vJ9QM","object":"chat.completion","created":1695324963,"model":"gpt-35-turbo","prompt_filter_results":[{"prompt_index":0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"choices":[{"index":0,"finish_reason":"function_call","message":{"role":"assistant"},"content_filter_results":{}}],"usage":{"completion_tokens":19,"prompt_tokens":425,"total_tokens":444}}'
    default_query = "hello"
    query = chat_approach.get_search_query(json.loads(payload), default_query)

    assert query == default_query
