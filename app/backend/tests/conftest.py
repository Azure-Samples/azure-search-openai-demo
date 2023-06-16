import pytest
import app as backend_app
from approaches.approach import Approach
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach


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


@pytest.fixture()
def app():
    backend_app.app.config.update(
        {
            "TESTING": True,
        }
    )
    backend_app.ask_approaches["mock"] = MockedAskApproach()
    backend_app.chat_approaches["mock"] = MockedChatApproach()
    yield backend_app.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
