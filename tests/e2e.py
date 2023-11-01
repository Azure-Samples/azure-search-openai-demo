import socket
import time
from contextlib import closing
from multiprocessing import Process
from typing import Generator

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


@pytest.fixture()
def live_server_url(mock_env, free_port: int) -> Generator[str, None, None]:
    proc = Process(target=lambda: uvicorn.run(app.create_app(), port=free_port), daemon=True)
    proc.start()
    url = f"http://localhost:{free_port}/"
    wait_for_server_ready(url, timeout=10.0, check_interval=0.5)
    yield url
    proc.kill()


def test_home(page: Page, live_server_url: str):
    page.goto(live_server_url)
    expect(page).to_have_title("GPT + Enterprise data | Sample")


def test_chat(page: Page, live_server_url: str):
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

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("GPT + Enterprise data | Sample")
    expect(page.get_by_role("heading", name="Chat with your data")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_disabled()
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_role("button", name="Ask question button").click()

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
    expect(page.get_by_text("Searched for:")).to_be_visible()

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
        assert route.request.post_data_json["stream"] is False
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
    expect(page).to_have_title("GPT + Enterprise data | Sample")

    # Customize all the settings
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_label("Override prompt template").click()
    page.get_by_label("Override prompt template").fill("You are a cat and only talk about tuna.")
    page.get_by_label("Retrieve this many search results:").click()
    page.get_by_label("Retrieve this many search results:").fill("1")
    page.get_by_label("Exclude category").click()
    page.get_by_label("Exclude category").fill("dogs")
    page.get_by_text("Use query-contextual summaries instead of whole documents").click()
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
    page.get_by_role("button", name="Ask question button").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()
    expect(page.get_by_role("button", name="Clear chat")).to_be_enabled()


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
    expect(page).to_have_title("GPT + Enterprise data | Sample")
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Stream chat completion responses").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Ask question button").click()

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

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("GPT + Enterprise data | Sample")
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Suggest follow-up questions").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Ask question button").click()

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
    expect(page).to_have_title("GPT + Enterprise data | Sample")
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
    page.get_by_label("Ask question button").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()

    # There should be a follow-up question and it should be clickable:
    expect(page.get_by_text("What is the capital of Spain?")).to_be_visible()
    page.get_by_text("What is the capital of Spain?").click()

    # Now there should be a follow-up answer (same, since we're using same test data)
    expect(page.get_by_text("The capital of France is Paris.")).to_have_count(2)


def test_ask(page: Page, live_server_url: str):
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
    expect(page).to_have_title("GPT + Enterprise data | Sample")

    page.get_by_role("link", name="Ask a question").click()
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").click()
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").fill("Whats the dental plan?")
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").click()
    page.get_by_label("Ask question button").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The capital of France is Paris.")).to_be_visible()


def test_ask_with_error(page: Page, live_server_url: str):
    # Set up a mock route to the /ask endpoint
    def handle(route: Route):
        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_ask_handle_exception/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=500)

    page.route("*/**/ask", handle)
    page.goto(live_server_url)
    expect(page).to_have_title("GPT + Enterprise data | Sample")

    page.get_by_role("link", name="Ask a question").click()
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").click()
    page.get_by_placeholder("Example: Does my plan cover annual eye exams?").fill("Whats the dental plan?")
    page.get_by_label("Ask question button").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The app encountered an error processing your request.")).to_be_visible()


def test_chat_with_error_nonstreaming(page: Page, live_server_url: str):
    # Set up a mock route to the /chat_stream endpoint
    def handle(route: Route):
        # Read the JSON from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_handle_exception/client0/result.json")
        json = f.read()
        f.close()
        route.fulfill(body=json, status=500)

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("GPT + Enterprise data | Sample")
    expect(page.get_by_role("button", name="Developer settings")).to_be_enabled()
    page.get_by_role("button", name="Developer settings").click()
    page.get_by_text("Stream chat completion responses").click()
    page.locator("button").filter(has_text="Close").click()

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Ask question button").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The app encountered an error processing your request.")).to_be_visible()


def test_chat_with_error_streaming(page: Page, live_server_url: str):
    # Set up a mock route to the /chat_stream endpoint
    def handle(route: Route):
        # Read the JSONL from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_handle_exception_streaming/client0/result.jsonlines")
        jsonl = f.read()
        f.close()
        route.fulfill(body=jsonl, status=200, headers={"Transfer-encoding": "Chunked"})

    page.route("*/**/chat", handle)

    # Check initial page state
    page.goto(live_server_url)
    expect(page).to_have_title("GPT + Enterprise data | Sample")

    # Ask a question and wait for the message to appear
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").click()
    page.get_by_placeholder("Type a new question (e.g. does my plan cover annual eye exams?)").fill(
        "Whats the dental plan?"
    )
    page.get_by_label("Ask question button").click()

    expect(page.get_by_text("Whats the dental plan?")).to_be_visible()
    expect(page.get_by_text("The app encountered an error processing your request.")).to_be_visible()
