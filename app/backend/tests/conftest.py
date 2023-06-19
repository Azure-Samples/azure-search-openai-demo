from collections import namedtuple
import pytest
from unittest import mock
from approaches.approach import Approach
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
import app as backend_app

class MockedAskApproach(Approach):
    def run(self, question, overrides):
        assert question == "What is the capital of France?"
        return {"answer": "Paris"}


class MockedChatApproach(Approach):
    def run(self, history, overrides):
        history_text = ChatReadRetrieveReadApproach.get_chat_history_as_text(
            self, history
        )
        assert "What is the capital of France?" in history_text
        assert "<|im_start|>" in history_text
        assert "<|im_end|>" in history_text
        return {"answer": "Paris"}


MockToken = namedtuple("MockToken", ["token", "expires_on"])


class MockAzureCredential:
    def get_token(self, uri):
        return MockToken("mock_token", 9999999999)


@pytest.fixture()
def app():
    # mock the DefaultAzureCredential
    with mock.patch(
        "app.DefaultAzureCredential"
    ) as mock_default_azure_credential:
        mock_default_azure_credential.return_value = MockAzureCredential()

        app = backend_app.create_app()
    app.config.update(
        {
            "TESTING": True,
            backend_app.CONFIG_ASK_APPROACHES: {"mock": MockedAskApproach()},
            backend_app.CONFIG_CHAT_APPROACHES: {"mock": MockedChatApproach()},
        }
    )

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
