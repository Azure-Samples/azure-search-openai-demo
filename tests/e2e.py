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
    # Set up a mock route to the /chat_stream endpoint
    def handle(route: Route):
        # Read the JSONL from our snapshot results and return as the response
        f = open("tests/snapshots/test_app/test_chat_stream_text/client0/result.jsonlines")
        jsonl = f.read()
        f.close()
        route.fulfill(body=jsonl, status=200, headers={"Transfer-encoding": "Chunked"})

    page.route("*/**/chat_stream", handle)

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
