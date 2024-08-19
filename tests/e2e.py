import json
import os
import socket
import time
from contextlib import closing
from multiprocessing import Process
from typing import Generator
from unittest import mock

import pytest
import requests
import uvicorn
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
            "USE_SPEECH_INPUT_BROWSER": "false",
            "USE_SPEECH_OUTPUT_AZURE": "false",
            "AZURE_SEARCH_INDEX": "test-search-index",
            "AZURE_SEARCH_SERVICE": "test-search-service",
            "AZURE_SPEECH_SERVICE_ID": "test-id",
            "AZURE_SPEECH_SERVICE_LOCATION": "eastus",
            "AZURE_OPENAI_SERVICE": "test-openai-service",
            "AZURE_OPENAI_CHATGPT_MODEL": "gpt-35-turbo",
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
        # Assert that session_state is specified in the request (None for now)
        session_state = route.request.post_data_json["session_state"]
        assert session_state is None
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


def test_chat_customization(page: Page, live_server_url: str):
    # Set up a mock route to the /chat endpoint
    def handle(route: Route):
        overrides = route.request.post_data_json["context"]["overrides"]
        assert overrides["retrieval_mode"] == "vectors"
        assert overrides["semantic_ranker"] is False
        assert overrides["semantic_captions"] is True
        assert overrides["top"] == 1
        assert overrides["prompt_template"] == "You are a cat and only talk about tuna."
        assert overrides["exclude_category"] == "dogs"
        assert overrides["use_oid_security_filter"] is False
        assert overrides["use_groups_security_filter"] is False

        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_text/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=200)

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Customize all the settings
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_label("Override prompt template").click()
    page.get_by_label("Override prompt template").fill("You are a cat and only talk about tuna.")
    page.get_by_label("Retrieve this many search results:").click()
    page.get_by_label("Retrieve this many search results:").fill("1")
    page.get_by_label("Exclude category").click()
    page.get_by_label("Exclude category").fill("dogs")
    page.get_by_text("Use semantic captions").click()
    page.get_by_text("Use semantic ranker for retrieval").click()
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


def test_chat_customization_gpt4v(page: Page, live_server_url: str):

    # Set up a mock route to the /chat endpoint
    def handle_chat(route: Route):
        overrides = route.request.post_data_json["context"]["overrides"]
        assert overrides["gpt4v_input"] == "images"
        assert overrides["use_gpt4v"] is True
        assert overrides["vector_fields"] == ["imageEmbedding"]

        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_text/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=200)

    def handle_config(route: Route):
        route.fulfill(
            body=json.dumps(
                {
                    "showGPT4VOptions": True,
                    "showSemanticRankerOption": True,
                    "showUserUpload": False,
                    "showVectorOption": True,
                }
            ),
            status=200,
        )

    page.route("*/**/config", handle_config)
    page.route("*/**/chat", handle_chat)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # Customize the GPT-4-vision settings
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Use GPT vision model").click()
    page.get_by_text("Images and text").click()
    page.get_by_role("option", name="Images", exact=True).click()
    page.get_by_text("Text and Image embeddings").click()
    page.get_by_role("option", name="Image Embeddings", exact=True).click()
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
        overrides = route.request.post_data_json["context"]["overrides"]
        assert overrides["suggest_followup_questions"] is True
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


def test_ask(sized_page: Page, live_server_url: str):
    page = sized_page

    # Set up a mock route to the /ask endpoint
    def handle(route: Route):
        # Assert that session_state is specified in the request (None for now)
        session_state = route.request.post_data_json["session_state"]
        assert session_state is None
        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_ask_rtr_hybrid/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=200)

    page.route("*/**/ask", handle)
    page.goto(live_server_url)
    expect(page).to_have_title("Azure OpenAI + AI Search")

    # The burger menu only exists at smaller viewport sizes
    if page.get_by_role("button", name="Toggle menu").is_visible():
        page.get_by_role("button", name="Toggle menu").click()
    page.get_by_role("link", name="Ask a question").click()
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").click()
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").fill("Whats the dental plan?")
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").click()
    page.get_by_label("Submit question").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()


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
                    "showGPT4VOptions": False,
                    "showSemanticRankerOption": True,
                    "showUserUpload": False,
                    "showVectorOption": True,
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
                    "showGPT4VOptions": False,
                    "showSemanticRankerOption": True,
                    "showUserUpload": True,
                    "showVectorOption": True,
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
