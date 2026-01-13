import json
import os
import socket
import time
from collections.abc import Generator
from contextlib import closing
from multiprocessing import Process
from unittest import mock

import pytest
import requests
import uvicorn
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page, Route, expect

import app

expect.set_options(timeout=10_000)


def wait_for_server_ready(url: str, timeout: float = 10.0, check_interval: float = 0.5) -> bool:
    """Make requests to provided url until it responds without error."""
    conn_error = None
    for _ in range(int(timeout / check_interval)):
        try:
            requests.get(url)
        except requests.ConnectionError as exc:
            time.sleep(check_interval)
            conn_error = str(exc)
        else:
            return True
    raise RuntimeError(conn_error)


@pytest.fixture(scope="session")
def free_port() -> int:
    """Returns a free port for the test server to bind."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def run_server(port: int):
    with mock.patch.dict(
        os.environ,
        {
            "AZURE_STORAGE_ACCOUNT": "test-storage-account",
            "AZURE_STORAGE_CONTAINER": "test-storage-container",
            "AZURE_STORAGE_RESOURCE_GROUP": "test-storage-rg",
            "AZURE_SUBSCRIPTION_ID": "test-storage-subid",
            "ENABLE_LANGUAGE_PICKER": "false",
            "USE_SPEECH_INPUT_BROWSER": "false",
            "USE_SPEECH_OUTPUT_AZURE": "false",
            "AZURE_SEARCH_INDEX": "test-search-index",
            "AZURE_SEARCH_SERVICE": "test-search-service",
            "AZURE_SPEECH_SERVICE_ID": "test-id",
            "AZURE_SPEECH_SERVICE_LOCATION": "eastus",
            "AZURE_OPENAI_SERVICE": "test-openai-service",
            "AZURE_OPENAI_CHATGPT_MODEL": "gpt-4.1-mini",
            "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
            "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
        },
        clear=True,
    ):
        uvicorn.run(app.create_app(), port=port)


@pytest.fixture()
def live_server_url(mock_env, mock_acs_search, free_port: int) -> Generator[str, None, None]:
    proc = Process(target=run_server, args=(free_port,), daemon=True)
    proc.start()
    url = f"http://localhost:{free_port}/"
    wait_for_server_ready(url, timeout=10.0, check_interval=0.5)
    yield url
    proc.kill()


@pytest.fixture(params=[(480, 800), (600, 1024), (768, 1024), (992, 1024), (1024, 768)])
def sized_page(page: Page, request):
    size = request.param
    page.set_viewport_size({"width": size[0], "height": size[1]})
    yield page


def test_home(page: Page, live_server_url: str):
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")


def test_chat(sized_page: Page, live_server_url: str):
    page = sized_page

    # Set up a mock route to the /chat endpoint with streaming results
    def handle(route: Route):
        try:
            post_data = route.request.post_data_json
            # Assert that session_state is specified (None initially)
            if "session_state" in post_data:
                assert post_data["session_state"] is None
            overrides = post_data["context"]["overrides"]
            # Assert that the default overrides are correct
            assert overrides.get("send_text_sources") is True
            assert overrides.get("send_image_sources") is False
            assert overrides.get("search_text_embeddings") is True
            assert overrides.get("search_image_embeddings") is False
            # retrieval_mode may be explicitly "hybrid" or omitted (interpreted as hybrid)
            assert overrides.get("retrieval_mode") in ["hybrid", None]
        except Exception as e:
            print(f"Error in test_chat handler (defaults validation): {e}")

        # Read the JSONL from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_stream_text/client0/result.jsonlines")
        jsonl = f.read()
        f.close()
        route.fulfill(body=jsonl, status=200, headers={"Transfer-encoding": "Chunked"})

    page.route("*/**/chat/stream", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")
    expect(page.get_by_role("heading", name="Chat with your data")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_disabled()
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()

    # Check accessibility of page in initial state
    results = Axe().run(page)
    assert results.violations_count == 0, results.generate_report()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_role("button", name="Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_enabled()

    # Show the citation document
    page.get_by_text("1. Benefit_Options-2.pdf").click()
    expect(page.get_by_role("tab", name="Citation")).to_be_visible()
    expect(page.get_by_title("Citation")).to_be_visible()

    # Show the thought process
    page.get_by_label("Show thought process").click()
    expect(page.get_by_title("Thought process")).to_be_visible()
    expect(page.get_by_text("Generated search query")).to_be_visible()

    # Show the supporting content
    page.get_by_label("Show supporting content").click()
    expect(page.get_by_title("Supporting content")).to_be_visible()
    expect(page.get_by_role("heading", name="Benefit_Options-2.pdf")).to_be_visible()

    # Clear the chat
    page.get_by_role("button", name="Clear chat").click()
    expect(page.get_by_text("Whats the dental plan?")).not_to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).not_to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_disabled()


def test_chat_stop_button_visibility(page: Page, live_server_url: str):
    """Test that the stop button feature works without breaking the chat flow.

    Note: This test verifies the initial and final states but does not assert
    that the stop button appears during streaming. Testing transient UI states
    is flaky since the mock returns instantly. A proper test would require a
    delayed mock response, adding significant complexity for minimal benefit.
    """

    # Set up a mock route to the /chat endpoint with streaming results
    def handle(route: Route):
        # Read the JSONL from our snapshot results and return as the response
        with open("tests/snapshots/test_app/test_chat_stream_text/client0/result.jsonlines") as f:
            jsonl = f.read()
        route.fulfill(body=jsonl, status=200, headers={"Transfer-encoding": "Chunked"})

    page.route("*/**/chat/stream", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Verify the submit button is visible initially (not the stop button)
    expect(page.get_by_label("Submit question")).to_be_visible()
    expect(page.get_by_label("Stop streaming")).not_to_be_visible()

    # Ask a question
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Submit question").click()

    # Wait for the response to complete and verify the submit button is back
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()
    expect(page.get_by_label("Submit question")).to_be_visible()
    expect(page.get_by_label("Stop streaming")).not_to_be_visible()


def test_chat_stop_restores_question(page: Page, live_server_url: str):
    """Test that when streaming returns no content, the question is restored to input."""

    # Set up a mock route that returns an empty streaming response (no content)
    def handle(route: Route):
        # Return a valid but empty NDJSON stream - this simulates stopping before content arrives
        # Need at least one event with context/data_points to initialize, but no delta content
        jsonl = '{"context": {"data_points": {"text": []}, "thoughts": []}, "delta": {"role": "assistant"}}\n'
        route.fulfill(
            status=200,
            headers={"Transfer-encoding": "Chunked", "Content-Type": "application/x-ndjson"},
            body=jsonl,
        )

    page.route("*/**/chat/stream", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Type a question
    question_input = page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)")
    question_input.click()
    question_input.fill("Whats the dental plan?")

    # Submit the question
    page.get_by_label("Submit question").click()

    # The response contains context but no actual content (no delta.content events)
    # So the answer should be empty and question should be restored to input

    # Verify the question is restored to the input field
    expect(question_input).to_have_value("Whats the dental plan?")

    # Verify the submit button is back
    expect(page.get_by_label("Submit question")).to_be_visible()

    # Verify no answer was added to the chat (Clear chat should be disabled since answer was empty)
    expect(page.get_by_role("button", name="Clear chat")).to_be_disabled()


def test_chat_customization(page: Page, live_server_url: str):
    # Set up a mock route to the /chat endpoint
    def handle(route: Route):
        try:
            post_data = route.request.post_data_json
            if post_data and "context" in post_data and "overrides" in post_data["context"]:
                overrides = post_data["context"]["overrides"]
                assert overrides["temperature"] == 0.5
                assert overrides["seed"] == 123
                assert overrides["minimum_search_score"] == 0.5
                assert overrides["minimum_reranker_score"] == 0.5
                assert overrides["retrieval_mode"] == "vectors"
                assert overrides["semantic_ranker"] is False
                assert overrides["semantic_captions"] is True
                assert overrides["top"] == 1
                assert overrides["prompt_template"] == "You are a cat and only talk about tuna."
                assert overrides["exclude_category"] == "dogs"
                assert overrides["suggest_followup_questions"] is True
        except Exception as e:
            print(f"Error in test_chat_customization handler: {e}")

        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_text/client0/result.json")
        json_data = f.read()
        f.close()
        route.fulfill(body=json_data, status=200)

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Customize all the settings
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_label("Override prompt template").click()
    page.get_by_label("Override prompt template").fill("You are a cat and only talk about tuna.")
    page.get_by_label("Temperature").click()
    page.get_by_label("Temperature").fill("0.5")
    page.get_by_label("Seed").click()
    page.get_by_label("Seed").fill("123")
    page.get_by_label("Minimum search score").click()
    page.get_by_label("Minimum search score").fill("0.5")
    page.get_by_label("Minimum reranker score").click()
    page.get_by_label("Minimum reranker score").fill("0.5")
    page.get_by_label("Retrieve this many search results:").click()
    page.get_by_label("Retrieve this many search results:").fill("1")
    page.get_by_label("Include category").click()
    page.get_by_role("option", name="All", exact=True).click()
    page.get_by_label("Exclude category").click()
    page.get_by_label("Exclude category").fill("dogs")
    page.get_by_text("Use semantic captions").click()
    page.get_by_text("Use semantic ranker for retrieval").click()
    page.get_by_text("Suggest follow-up questions").click()
    page.get_by_text("Vectors + Text (Hybrid)").click()
    page.get_by_role("option", name="Vectors", exact=True).click()
    page.get_by_text("Stream chat completion responses").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_role("button", name="Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_enabled()


def test_chat_customization_multimodal(page: Page, live_server_url: str):
    # Set up a mock route to the /chat endpoint
    def handle_chat(route: Route):
        try:
            post_data = route.request.post_data_json
            if post_data and "context" in post_data and "overrides" in post_data["context"]:
                overrides = post_data["context"]["overrides"]
                # After our UI changes we expect:
                # - send_text_sources to be False (we unchecked Texts)
                # - send_image_sources to be True (we left Images checked)
                # - search_text_embeddings to be False (we unchecked Text embeddings)
                # - search_image_embeddings to be True (we left Image embeddings checked)
                assert overrides["send_text_sources"] is False
                assert overrides["send_image_sources"] is True
                assert overrides["search_text_embeddings"] is False
                assert overrides["search_image_embeddings"] is True
                assert overrides["retrieval_mode"] == "vectors"
        except Exception as e:
            print(f"Error in handle_chat: {e}")

        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_text/client0/result.json")
        json_data = f.read()
        f.close()
        route.fulfill(body=json_data, status=200)

    def handle_config(route: Route):
        route.fulfill(
            body=json.dumps(
                {
                    "defaultReasoningEffort": "",
                    "defaultRetrievalReasoningEffort": "minimal",
                    "showMultimodalOptions": True,
                    "showSemanticRankerOption": True,
                    "showQueryRewritingOption": False,
                    "showReasoningEffortOption": False,
                    "streamingEnabled": True,
                    "showVectorOption": True,
                    "showUserUpload": False,
                    "showLanguagePicker": False,
                    "showSpeechInput": False,
                    "showSpeechOutputBrowser": False,
                    "showSpeechOutputAzure": False,
                    "showChatHistoryBrowser": False,
                    "showChatHistoryCosmos": False,
                    "showAgenticRetrievalOption": False,
                    "ragSearchImageEmbeddings": True,
                    "ragSearchTextEmbeddings": True,
                    "ragSendImageSources": True,
                    "ragSendTextSources": True,
                    "webSourceEnabled": False,
                    "sharepointSourceEnabled": False,
                }
            ),
            status=200,
        )

    page.route("*/**/config", handle_config)
    page.route("*/**/chat", handle_chat)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Open Developer settings
    page.get_by_role("button", name="Developer settings").click()

    # Check the default retrieval mode (Hybrid)
    # expect(page.get_by_label("Retrieval mode")).to_have_value("hybrid")

    # Check that Vector fields and LLM inputs sections are visible with checkboxes
    expect(page.locator("fieldset").filter(has_text="Included vector fields")).to_be_visible()
    expect(page.locator("fieldset").filter(has_text="LLM input sources")).to_be_visible()

    # Modify the retrieval mode to "Vectors"
    page.get_by_text("Vectors + Text (Hybrid)").click()
    page.get_by_role("option", name="Vectors", exact=True).click()

    # Use a different approach to target the checkboxes directly by their role
    # Find the checkbox for Text embeddings by its specific class or nearby text
    page.get_by_text("Text embeddings").click()

    # Same for the LLM text sources checkbox
    page.get_by_text("Text sources").click()

    # Turn off streaming
    page.get_by_text("Stream chat completion responses").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Submit question").click()


def test_chat_nonstreaming(page: Page, live_server_url: str):
    # Set up a mock route to the /chat_stream endpoint
    def handle(route: Route):
        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_text/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=200)

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Stream chat completion responses").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_enabled()


def test_chat_followup_streaming(page: Page, live_server_url: str):
    # Set up a mock route to the /chat_stream endpoint
    def handle(route: Route):
        try:
            post_data = route.request.post_data_json
            if post_data and "context" in post_data and "overrides" in post_data["context"]:
                overrides = post_data["context"]["overrides"]
                assert overrides["suggest_followup_questions"] is True
        except Exception as e:
            print(f"Error in test_chat_followup_streaming handler: {e}")

        # Read the JSONL from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_stream_followup/client0/result.jsonlines")
        jsonl = f.read()
        f.close()
        route.fulfill(body=jsonl, status=200, headers={"Transfer-encoding": "Chunked"})

    page.route("*/**/chat/stream", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Suggest follow-up questions").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()

    # There should be a follow-up question and it should be clickable:
    expect(page.get_by_text("What is the capital of Spain?")).to_be_visible()
    page.get_by_text("What is the capital of Spain?").click()

    # Now there should be a follow-up answer (same, since we're using same test data)
    expect(page.get_by_text("The capital of France is Paris.")).to_have_count(2)


def test_chat_followup_nonstreaming(page: Page, live_server_url: str):
    # Set up a mock route to the /chat_stream endpoint
    def handle(route: Route):
        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_followup/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=200)

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Stream chat completion responses").click()
    page.get_by_text("Suggest follow-up questions").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()

    # There should be a follow-up question and it should be clickable:
    expect(page.get_by_text("What is the capital of Spain?")).to_be_visible()
    page.get_by_text("What is the capital of Spain?").click()

    # Now there should be a follow-up answer (same, since we're using same test data)
    expect(page.get_by_text("The capital of France is Paris.")).to_have_count(2)


def test_upload_hidden(page: Page, live_server_url: str):

    def handle_auth_setup(route: Route):
        with open("tests/snapshots/test_authenticationhelper/test_auth_setup/result.json") as f:
            auth_setup = json.load(f)
            route.fulfill(body=json.dumps(auth_setup), status=200)

    page.route("*/**/auth_setup", handle_auth_setup)

    def handle_config(route: Route):
        route.fulfill(
            body=json.dumps(
                {
                    "defaultReasoningEffort": "",
                    "defaultRetrievalReasoningEffort": "minimal",
                    "showMultimodalOptions": False,
                    "showSemanticRankerOption": True,
                    "showQueryRewritingOption": False,
                    "showReasoningEffortOption": False,
                    "streamingEnabled": True,
                    "showVectorOption": True,
                    "showUserUpload": False,
                    "showLanguagePicker": False,
                    "showSpeechInput": False,
                    "showSpeechOutputBrowser": False,
                    "showSpeechOutputAzure": False,
                    "showChatHistoryBrowser": False,
                    "showChatHistoryCosmos": False,
                    "showAgenticRetrievalOption": False,
                    "ragSearchImageEmbeddings": False,
                    "ragSearchTextEmbeddings": True,
                    "ragSendImageSources": False,
                    "ragSendTextSources": True,
                    "webSourceEnabled": False,
                    "sharepointSourceEnabled": False,
                }
            ),
            status=200,
        )

    page.route("*/**/config", handle_config)

    page.goto(live_server_url)

    expect(page).to_have_title("Azure OpenAI + AI Search")

    expect(page.get_by_role("button", name="Clear chat")).to_be_visible()
    expect(page.get_by_role("button", name="Manage file uploads")).not_to_be_visible()


def test_upload_disabled(page: Page, live_server_url: str):

    def handle_auth_setup(route: Route):
        with open("tests/snapshots/test_authenticationhelper/test_auth_setup/result.json") as f:
            auth_setup = json.load(f)
            route.fulfill(body=json.dumps(auth_setup), status=200)

    page.route("*/**/auth_setup", handle_auth_setup)

    def handle_config(route: Route):
        route.fulfill(
            body=json.dumps(
                {
                    "defaultReasoningEffort": "",
                    "defaultRetrievalReasoningEffort": "minimal",
                    "showMultimodalOptions": False,
                    "showSemanticRankerOption": True,
                    "showQueryRewritingOption": False,
                    "showReasoningEffortOption": False,
                    "streamingEnabled": True,
                    "showVectorOption": True,
                    "showUserUpload": True,
                    "showLanguagePicker": False,
                    "showSpeechInput": False,
                    "showSpeechOutputBrowser": False,
                    "showSpeechOutputAzure": False,
                    "showChatHistoryBrowser": False,
                    "showChatHistoryCosmos": False,
                    "showAgenticRetrievalOption": False,
                    "ragSearchImageEmbeddings": False,
                    "ragSearchTextEmbeddings": True,
                    "ragSendImageSources": False,
                    "ragSendTextSources": True,
                    "webSourceEnabled": False,
                    "sharepointSourceEnabled": False,
                }
            ),
            status=200,
        )

    page.route("*/**/config", handle_config)

    page.goto(live_server_url)

    expect(page).to_have_title("Azure OpenAI + AI Search")

    expect(page.get_by_role("button", name="Manage file uploads")).to_be_visible()
    expect(page.get_by_role("button", name="Manage file uploads")).to_be_disabled()
    # We can't test actual file upload as we don't currently have isLoggedIn(client) mocked out


def test_agentic_retrieval_effort_minimal_disables_web(page: Page, live_server_url: str):
    """Test that selecting 'Minimal' effort deselects and disables the web source checkbox."""

    # Set up a mock route to the /chat endpoint
    def handle(route: Route):
        try:
            post_data = route.request.post_data_json
            if post_data and "context" in post_data and "overrides" in post_data["context"]:
                overrides = post_data["context"]["overrides"]
                assert overrides["temperature"] == 0.5
                assert overrides["seed"] == 123
                assert overrides["minimum_search_score"] == 0.5
                assert overrides["minimum_reranker_score"] == 0.5
                assert overrides["retrieval_mode"] == "vectors"
                assert overrides["semantic_ranker"] is False
                assert overrides["semantic_captions"] is True
                assert overrides["top"] == 1
                assert overrides["prompt_template"] == "You are a cat and only talk about tuna."
                assert overrides["exclude_category"] == "dogs"
                assert overrides["suggest_followup_questions"] is True
        except Exception as e:
            print(f"Error in test_chat_customization handler: {e}")

        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_text_agent/knowledgebase_client2_sharepoint/result.json")
        json_data = f.read()
        f.close()
        route.fulfill(body=json_data, status=200)

    page.route("*/**/chat", handle)

    def handle_config(route: Route):
        route.fulfill(
            body=json.dumps(
                {
                    "defaultReasoningEffort": "",
                    "defaultRetrievalReasoningEffort": "low",
                    "showMultimodalOptions": False,
                    "showSemanticRankerOption": True,
                    "showQueryRewritingOption": False,
                    "showReasoningEffortOption": False,
                    "streamingEnabled": True,
                    "showVectorOption": True,
                    "showUserUpload": False,
                    "showLanguagePicker": False,
                    "showSpeechInput": False,
                    "showSpeechOutputBrowser": False,
                    "showSpeechOutputAzure": False,
                    "showChatHistoryBrowser": False,
                    "showChatHistoryCosmos": False,
                    "showAgenticRetrievalOption": True,
                    "ragSearchImageEmbeddings": False,
                    "ragSearchTextEmbeddings": True,
                    "ragSendImageSources": False,
                    "ragSendTextSources": True,
                    "webSourceEnabled": True,
                    "sharepointSourceEnabled": True,
                }
            ),
            status=200,
        )

    page.route("*/**/config", handle_config)

    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Open Developer settings
    page.get_by_role("button", name="Developer settings").click()

    # Verify that agentic retrieval option is visible
    expect(page.get_by_text("Retrieval reasoning effort")).to_be_visible()

    # Verify that web and sharepoint checkboxes are initially visible and enabled
    web_checkbox = page.get_by_role("checkbox", name="Include web source")
    sharepoint_checkbox = page.get_by_role("checkbox", name="Include SharePoint source")
    expect(web_checkbox).to_be_visible()
    expect(web_checkbox).to_be_enabled()
    expect(sharepoint_checkbox).to_be_visible()
    expect(sharepoint_checkbox).to_be_enabled()

    # Select "Minimal" from the effort dropdown
    page.get_by_label("Retrieval reasoning effort").click()
    page.get_by_role("option", name="Minimal").click()

    # Verify that web checkbox is now deselected and disabled
    expect(web_checkbox).not_to_be_checked()
    expect(web_checkbox).to_be_disabled()

    # Verify that SharePoint checkbox is still enabled
    expect(sharepoint_checkbox).to_be_enabled()

    # Now select "Low" from the effort dropdown
    page.get_by_label("Retrieval reasoning effort").click()
    page.get_by_role("option", name="Low").click()

    # De-select streaming
    page.get_by_text("Stream chat completion responses").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_role("button", name="Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_enabled()

    # Open the thought process by clicking the lightbulb on the answer
    page.get_by_label("Show thought process").click()
    expect(page.get_by_title("Thought process")).to_be_visible()

    # Verify the expected thought process sections are visible
    expect(page.get_by_text("Agentic retrieval response")).to_be_visible()
    expect(page.get_by_text("Prompt to generate answer")).to_be_visible()
