def test_ask_with_unknown_approach(client):
    response = client.post("/ask", json={"approach": "test"})
    assert response.status_code == 400


def test_ask_mock_approach(client):
    response = client.post(
        "/ask", json={"approach": "mock", "question": "What is the capital of France?"}
    )
    assert response.status_code == 200
    assert response.json["answer"] == "Paris"


def test_chat_with_unknown_approach(client):
    response = client.post("/chat", json={"approach": "test"})
    assert response.status_code == 400


def test_chat_mock_approach(client):
    response = client.post(
        "/chat",
        json={
            "approach": "mock",
            "history": [{"user": "What is the capital of France?"}],
        },
    )
    assert response.status_code == 200
    assert response.json["answer"] == "Paris"
