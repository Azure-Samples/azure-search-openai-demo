from collections import namedtuple
from unittest import mock

import pytest

import app as backend_app
from approaches.approach import Approach
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach


class MockedAskApproach(Approach):
    def run(self, question, overrides):
        assert question == "What is the capital of France?"
        return {"answer": "Paris"}


class MockedChatApproach(ChatReadRetrieveReadApproach):
    def __init__(self):
        pass

    def run(self, history, overrides):
        messages = ChatReadRetrieveReadApproach.get_messages_from_history(self, ChatReadRetrieveReadApproach.query_prompt_template, "gpt-3.5-turbo", history, "Generate search query")
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "Generate search query"
        assert messages[1]["role"] == "user"
        return {"answer": "Paris", "data_points": [], "thoughts": ""}


MockToken = namedtuple("MockToken", ["token", "expires_on"])


class MockAzureCredential:
    def get_token(self, uri):
        return MockToken("mock_token", 9999999999)


@pytest.fixture()
def app():
    # mock the DefaultAzureCredential
    with mock.patch("app.DefaultAzureCredential") as mock_default_azure_credential:
        mock_default_azure_credential.return_value = MockAzureCredential()
        _app = backend_app.create_app()
    _app.config.update(
        {
            "TESTING": True,
            backend_app.CONFIG_ASK_APPROACHES: {"mock": MockedAskApproach()},
            backend_app.CONFIG_CHAT_APPROACHES: {"mock": MockedChatApproach()},
        }
    )

    yield _app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
