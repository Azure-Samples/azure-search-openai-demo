import json
import os
from unittest import mock

import pytest
import quart.testing.app
from httpx import Request, Response
from openai import BadRequestError

import app


def fake_response(http_code):
    return Response(http_code, request=Request(method="get", url="https://foo.bar/"))


# See https://learn.microsoft.com/azure/ai-services/openai/concepts/content-filter
filtered_response = BadRequestError(
    message="The response was filtered",
    body={
        "message": "The response was filtered",
        "type": None,
        "param": "prompt",
        "code": "content_filter",
        "status": 400,
    },
    response=Response(
        400, request=Request(method="get", url="https://foo.bar/"), json={"error": {"code": "content_filter"}}
    ),
)

contextlength_response = BadRequestError(
    message="This model's maximum context length is 4096 tokens. However, your messages resulted in 5069 tokens. Please reduce the length of the messages.",
    body={
        "message": "This model's maximum context length is 4096 tokens. However, your messages resulted in 5069 tokens. Please reduce the length of the messages.",
        "code": "context_length_exceeded",
        "status": 400,
    },
    response=Response(400, request=Request(method="get", url="https://foo.bar/"), json={"error": {"code": "429"}}),
)


def messages_contains_text(messages, text):
    for message in messages:
        if text in message["content"]:
            return True
    return False


@pytest.mark.asyncio
async def test_missing_env_vars():
    with mock.patch.dict(os.environ, clear=True):
        quart_app = app.create_app()

        with pytest.raises(quart.testing.app.LifespanError, match="Error during startup 'AZURE_STORAGE_ACCOUNT'"):
            async with quart_app.test_app() as test_app:
                test_app.test_client()


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_redirect(client):
    response = await client.get("/redirect")
    assert response.status_code == 200
    assert (await response.get_data()) == b""


@pytest.mark.asyncio
async def test_favicon(client):
    response = await client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.content_type.startswith("image")
    assert response.content_type.endswith("icon")


@pytest.mark.asyncio
async def test_cors_notallowed(client) -> None:
    response = await client.get("/", headers={"Origin": "https://quart.com"})
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_allowed(client) -> None:
    response = await client.get("/", headers={"Origin": "https://frontend.com"})
    assert response.access_control_allow_origin == "https://frontend.com"
    assert "Access-Control-Allow-Origin" in response.headers


@pytest.mark.asyncio
async def test_ask_request_must_be_json(client):
    response = await client.post("/ask")
    assert response.status_code == 415
    result = await response.get_json()
    assert result["error"] == "request must be json"


@pytest.mark.asyncio
async def test_ask_handle_exception(client, monkeypatch, snapshot, caplog):
    monkeypatch.setattr(
        "approaches.retrievethenread.RetrieveThenReadApproach.run",
        mock.Mock(side_effect=ZeroDivisionError("something bad happened")),
    )

    response = await client.post(
        "/ask",
        json={"messages": [{"content": "What is the capital of France?", "role": "user"}]},
    )
    assert response.status_code == 500
    result = await response.get_json()
    assert "Exception in /ask: something bad happened" in caplog.text
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_handle_exception_contentsafety(client, monkeypatch, snapshot, caplog):
    monkeypatch.setattr(
        "approaches.retrievethenread.RetrieveThenReadApproach.run",
        mock.Mock(side_effect=filtered_response),
    )

    response = await client.post(
        "/ask",
        json={"messages": [{"content": "How do I do something bad?", "role": "user"}]},
    )
    assert response.status_code == 400
    result = await response.get_json()
    assert "Exception in /ask: The response was filtered" in caplog.text
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_handle_exception_contextlength(client, monkeypatch, snapshot, caplog):
    monkeypatch.setattr(
        "approaches.retrievethenread.RetrieveThenReadApproach.run",
        mock.Mock(side_effect=contextlength_response),
    )

    response = await client.post(
        "/ask",
        json={"messages": [{"content": "Super long message with lots of sources.", "role": "user"}]},
    )
    assert response.status_code == 500
    result = await response.get_json()
    assert (
        "Exception in /ask: This model's maximum context length is 4096 tokens. However, your messages resulted in 5069 tokens. Please reduce the length of the messages."
        in caplog.text
    )
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text_agent(agent_client, snapshot):
    response = await agent_client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "use_agentic_retrieval": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text_filter(auth_client, snapshot):
    response = await auth_client.post(
        "/ask",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "retrieval_mode": "text",
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                },
            },
        },
    )
    assert response.status_code == 200
    assert (
        auth_client.config[app.CONFIG_SEARCH_CLIENT].filter
        == "category ne 'excluded' and (oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text_agent_filter(agent_auth_client, snapshot):
    response = await agent_auth_client.post(
        "/ask",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "retrieval_mode": "text",
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                    "use_agentic_retrieval": True,
                },
            },
        },
    )
    assert response.status_code == 200
    assert (
        agent_auth_client.config[app.CONFIG_AGENT_CLIENT].filter
        == "category ne 'excluded' and (oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text_filter_public_documents(auth_public_documents_client, snapshot):
    response = await auth_public_documents_client.post(
        "/ask",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "retrieval_mode": "text",
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                },
            },
        },
    )
    assert response.status_code == 200
    assert (
        auth_public_documents_client.config[app.CONFIG_SEARCH_CLIENT].filter
        == "category ne 'excluded' and ((oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) or (not oids/any() and not groups/any()))"
    )
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text_semanticranker(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "semantic_ranker": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_text_semanticcaptions(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "semantic_captions": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_rtr_hybrid(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "hybrid"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_request_must_be_json(client):
    response = await client.post("/chat")
    assert response.status_code == 415
    result = await response.get_json()
    assert result["error"] == "request must be json"


@pytest.mark.asyncio
async def test_chat_stream_request_must_be_json(client):
    response = await client.post("/chat/stream")
    assert response.status_code == 415
    result = await response.get_json()
    assert result["error"] == "request must be json"


@pytest.mark.asyncio
async def test_chat_handle_exception(client, monkeypatch, snapshot, caplog):
    monkeypatch.setattr(
        "approaches.chatreadretrieveread.ChatReadRetrieveReadApproach.run",
        mock.Mock(side_effect=ZeroDivisionError("something bad happened")),
    )

    response = await client.post(
        "/chat",
        json={"messages": [{"content": "What is the capital of France?", "role": "user"}]},
    )
    assert response.status_code == 500
    result = await response.get_json()
    assert "Exception in /chat: something bad happened" in caplog.text
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_stream_handle_exception(client, monkeypatch, snapshot, caplog):
    monkeypatch.setattr(
        "approaches.chatreadretrieveread.ChatReadRetrieveReadApproach.run_stream",
        mock.Mock(side_effect=ZeroDivisionError("something bad happened")),
    )

    response = await client.post(
        "/chat/stream",
        json={"messages": [{"content": "What is the capital of France?", "role": "user"}]},
    )
    assert response.status_code == 500
    result = await response.get_json()
    assert "Exception in /chat: something bad happened" in caplog.text
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_handle_exception_contentsafety(client, monkeypatch, snapshot, caplog):
    monkeypatch.setattr(
        "approaches.chatreadretrieveread.ChatReadRetrieveReadApproach.run",
        mock.Mock(side_effect=filtered_response),
    )

    response = await client.post(
        "/chat",
        json={"messages": [{"content": "How do I do something bad?", "role": "user"}]},
    )
    assert response.status_code == 400
    result = await response.get_json()
    assert "Exception in /chat: The response was filtered" in caplog.text
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_handle_exception_streaming(client, monkeypatch, snapshot, caplog):
    chat_client = client.app.config[app.CONFIG_OPENAI_CLIENT]
    monkeypatch.setattr(
        chat_client.chat.completions, "create", mock.Mock(side_effect=ZeroDivisionError("something bad happened"))
    )

    response = await client.post(
        "/chat/stream",
        json={"messages": [{"content": "What is the capital of France?", "role": "user"}]},
    )
    assert response.status_code == 200
    assert "Exception while generating response stream: something bad happened" in caplog.text
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_handle_exception_contentsafety_streaming(client, monkeypatch, snapshot, caplog):
    chat_client = client.app.config[app.CONFIG_OPENAI_CLIENT]
    monkeypatch.setattr(chat_client.chat.completions, "create", mock.Mock(side_effect=filtered_response))

    response = await client.post(
        "/chat/stream",
        json={"messages": [{"content": "How do I do something bad?", "role": "user"}]},
    )
    assert response.status_code == 200
    assert "Exception while generating response stream: The response was filtered" in caplog.text
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_speech(client, mock_speech_success):
    response = await client.post(
        "/speech",
        json={
            "text": "test",
        },
    )
    assert response.status_code == 200
    assert await response.get_data() == b"mock_audio_data"


@pytest.mark.asyncio
async def test_speech_token_refresh(client_with_expiring_token, mock_speech_success):
    # First time should create a brand new token
    response = await client_with_expiring_token.post(
        "/speech",
        json={
            "text": "test",
        },
    )
    assert response.status_code == 200
    assert await response.get_data() == b"mock_audio_data"

    response = await client_with_expiring_token.post(
        "/speech",
        json={
            "text": "test",
        },
    )
    assert response.status_code == 200
    assert await response.get_data() == b"mock_audio_data"

    response = await client_with_expiring_token.post(
        "/speech",
        json={
            "text": "test",
        },
    )
    assert response.status_code == 200
    assert await response.get_data() == b"mock_audio_data"


@pytest.mark.asyncio
async def test_speech_request_must_be_json(client, mock_speech_success):
    response = await client.post("/speech")
    assert response.status_code == 415
    result = await response.get_json()
    assert result["error"] == "request must be json"


@pytest.mark.asyncio
async def test_speech_request_cancelled(client, mock_speech_cancelled):
    response = await client.post(
        "/speech",
        json={
            "text": "test",
        },
    )
    assert response.status_code == 500
    result = await response.get_json()
    assert result["error"] == "Speech synthesis canceled. Check logs for details."


@pytest.mark.asyncio
async def test_speech_request_failed(client, mock_speech_failed):
    response = await client.post(
        "/speech",
        json={
            "text": "test",
        },
    )
    assert response.status_code == 500
    result = await response.get_json()
    assert result["error"] == "Speech synthesis failed. Check logs for details."


@pytest.mark.asyncio
async def test_chat_text(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is False
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is False
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_agent(agent_client, snapshot):
    response = await agent_client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"use_agentic_retrieval": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][0]["props"]["max_docs_for_reranker"] == 500
    assert result["context"]["thoughts"][0]["props"]["reranker_threshold"] == 0
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_filter(auth_client, snapshot):
    response = await auth_client.post(
        "/chat",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "retrieval_mode": "text",
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                },
            },
        },
    )
    assert response.status_code == 200
    assert (
        auth_client.config[app.CONFIG_SEARCH_CLIENT].filter
        == "category ne 'excluded' and (oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_filter_agent(agent_auth_client, snapshot):
    response = await agent_auth_client.post(
        "/chat",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "use_agentic_retrieval": True,
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                },
            },
        },
    )
    assert response.status_code == 200
    assert (
        agent_auth_client.config[app.CONFIG_AGENT_CLIENT].filter
        == "category ne 'excluded' and (oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_filter_public_documents(auth_public_documents_client, snapshot):
    response = await auth_public_documents_client.post(
        "/chat",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "retrieval_mode": "text",
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                },
            },
        },
    )
    assert response.status_code == 200
    assert (
        auth_public_documents_client.config[app.CONFIG_SEARCH_CLIENT].filter
        == "category ne 'excluded' and ((oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) or (not oids/any() and not groups/any()))"
    )
    result = await response.get_json()
    if result.get("session_state"):
        del result["session_state"]
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_semanticranker(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "semantic_ranker": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_semanticcaptions(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "semantic_captions": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_prompt_template(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "prompt_template": "You are a cat."},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][3]["description"][0]["content"].startswith("You are a cat.")
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_prompt_template(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "prompt_template": "You are a cat."},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][2]["description"][0]["content"].startswith("You are a cat.")
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_prompt_template_concat(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "prompt_template": ">>> Meow like a cat."},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][3]["description"][0]["content"].startswith("Assistant helps")
    assert result["context"]["thoughts"][3]["description"][0]["content"].endswith("Meow like a cat.")
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_prompt_template_concat(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "prompt_template": ">>> Meow like a cat."},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][2]["description"][0]["content"].startswith("You are an intelligent assistant")
    assert result["context"]["thoughts"][2]["description"][0]["content"].endswith("Meow like a cat.")
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_seed(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"seed": 42},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_hybrid(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "hybrid"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is False
    assert result["context"]["thoughts"][1]["props"]["use_semantic_captions"] is False
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_hybrid_semantic_ranker(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "hybrid", "semantic_ranker": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_captions"] is False
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_hybrid_semantic_captions(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "hybrid", "semantic_ranker": True, "semantic_captions": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_captions"] is True
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_vector(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "vectors"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is False
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is False
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_vector_semantic_ranker(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "vectors", "semantic_ranker": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is False
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is True
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_text_semantic_ranker(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text", "semantic_ranker": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][1]["props"]["use_text_search"] is True
    assert result["context"]["thoughts"][1]["props"]["use_vector_search"] is False
    assert result["context"]["thoughts"][1]["props"]["use_semantic_ranker"] is True
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_stream_text(client, snapshot):
    response = await client.post(
        "/chat/stream",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_text_reasoning(reasoning_client, snapshot):
    response = await reasoning_client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["thoughts"][0]["props"]["token_usage"] is not None
    assert result["context"]["thoughts"][0]["props"]["reasoning_effort"] is not None
    assert result["context"]["thoughts"][3]["props"]["token_usage"] is not None
    assert result["context"]["thoughts"][3]["props"]["token_usage"]["reasoning_tokens"] > 0
    assert result["context"]["thoughts"][3]["props"]["reasoning_effort"] == os.getenv("AZURE_OPENAI_REASONING_EFFORT")

    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_stream_text_reasoning(reasoning_client, snapshot):
    response = await reasoning_client.post(
        "/chat/stream",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_stream_text_filter(auth_client, snapshot):
    response = await auth_client.post(
        "/chat/stream",
        headers={"Authorization": "Bearer MockToken"},
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {
                    "retrieval_mode": "text",
                    "use_oid_security_filter": True,
                    "use_groups_security_filter": True,
                    "exclude_category": "excluded",
                }
            },
        },
    )
    assert response.status_code == 200
    assert (
        auth_client.config[app.CONFIG_SEARCH_CLIENT].filter
        == "category ne 'excluded' and (oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_with_history(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [
                {"content": "What happens in a performance review?", "role": "user"},
                {
                    "content": "During a performance review, employees will receive feedback on their performance over the past year, including both successes and areas for improvement. The feedback will be provided by the employee's supervisor and is intended to help the employee develop and grow in their role [employee_handbook-3.pdf]. The review is a two-way dialogue between the employee and their manager, so employees are encouraged to be honest and open during the process [employee_handbook-3.pdf]. The employee will also have the opportunity to discuss their goals and objectives for the upcoming year [employee_handbook-3.pdf]. A written summary of the performance review will be provided to the employee, which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
                    "role": "assistant",
                },
                {"content": "Is dental covered?", "role": "user"},
            ],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert messages_contains_text(result["context"]["thoughts"][3]["description"], "performance review")
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_session_state_persists(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
            "session_state": {"conversation_id": 1234},
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_stream_session_state_persists(client, snapshot):
    response = await client.post(
        "/chat/stream",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"retrieval_mode": "text"},
            },
            "session_state": {"conversation_id": 1234},
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_followup(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"suggest_followup_questions": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["context"]["followup_questions"][0] == "What is the capital of Spain?"

    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_stream_followup(client, snapshot):
    response = await client.post(
        "/chat/stream",
        json={
            "messages": [{"content": "What is the capital of France?", "role": "user"}],
            "context": {
                "overrides": {"suggest_followup_questions": True},
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_vision(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "Are interest rates high?", "role": "user"}],
            "context": {
                "overrides": {
                    "use_gpt4v": True,
                    "gpt4v_input": "textAndImages",
                    "vector_fields": "textAndImageEmbeddings",
                },
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_chat_stream_vision(client, snapshot):
    response = await client.post(
        "/chat/stream",
        json={
            "messages": [{"content": "Are interest rates high?", "role": "user"}],
            "context": {
                "overrides": {
                    "use_gpt4v": True,
                    "gpt4v_input": "textAndImages",
                    "vector_fields": "textAndImageEmbeddings",
                },
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_vision_vectors(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [{"content": "Are interest rates high?", "role": "user"}],
            "context": {
                "overrides": {
                    "use_gpt4v": True,
                    "gpt4v_input": "textAndImages",
                    "vector_fields": "textAndImageEmbeddings",
                    "retrieval_mode": "vectors",
                },
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_ask_vision(client, snapshot):
    response = await client.post(
        "/ask",
        json={
            "messages": [{"content": "Are interest rates high?", "role": "user"}],
            "context": {
                "overrides": {
                    "use_gpt4v": True,
                    "gpt4v_input": "textAndImages",
                    "vector_fields": "textAndImageEmbeddings",
                },
            },
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


@pytest.mark.asyncio
async def test_format_as_ndjson():
    async def gen():
        yield {"a": "I ❤️ 🐍"}
        yield {"b": "Newlines inside \n strings are fine"}

    result = [line async for line in app.format_as_ndjson(gen())]
    assert result == ['{"a": "I ❤️ 🐍"}\n', '{"b": "Newlines inside \\n strings are fine"}\n']
