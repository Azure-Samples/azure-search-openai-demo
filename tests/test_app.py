import pytest


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ask_request_must_be_json(client):
    response = await client.post("/ask")
    assert response.status_code == 415
    result = await response.get_json()
    assert result["error"] == "request must be json"


@pytest.mark.asyncio
async def test_ask_with_unknown_approach(client):
    response = await client.post("/ask", json={"approach": "test"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_ask_mock_approach(client):
    response = await client.post("/ask", json={"approach": "mock", "question": "What is the capital of France?"})
    assert response.status_code == 200
    result = await response.get_json()
    assert result["answer"] == "Paris"


@pytest.mark.asyncio
async def test_chat_request_must_be_json(client):
    response = await client.post("/chat")
    assert response.status_code == 415
    result = await response.get_json()
    assert result["error"] == "request must be json"


@pytest.mark.asyncio
async def test_chat_with_unknown_approach(client):
    response = await client.post("/chat", json={"approach": "test"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_mock_approach(client):
    response = await client.post(
        "/chat",
        json={
            "approach": "mock",
            "history": [{"user": "What is the capital of France?"}],
        },
    )
    assert response.status_code == 200
    result = await response.get_json()
    assert result["answer"] == "Paris"
