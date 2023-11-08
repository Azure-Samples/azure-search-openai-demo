import io
import json
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import AsyncGenerator

import aiohttp
import openai
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import (
    Blueprint,
    Quart,
    abort,
    current_app,
    jsonify,
    make_response,
    request,
    send_file,
    send_from_directory,
)
from quart_cors import cors

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.retrievethenread import RetrieveThenReadApproach
from core.authentication import AuthenticationHelper

CONFIG_OPENAI_TOKEN = "openai_token"
CONFIG_CREDENTIAL = "azure_credential"
CONFIG_ASK_APPROACH = "ask_approach"
CONFIG_CHAT_APPROACH = "chat_approach"
CONFIG_BLOB_CONTAINER_CLIENT = "blob_container_client"
CONFIG_AUTH_CLIENT = "auth_client"
CONFIG_SEARCH_CLIENT = "search_client"
ERROR_MESSAGE = """The app encountered an error processing your request.
If you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.
Error type: {error_type}
"""

bp = Blueprint("routes", __name__, static_folder="static")
# Fix Windows registry issue with mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


@bp.route("/")
async def index():
    return await bp.send_static_file("index.html")


# Empty page is recommended for login redirect to work.
# See https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/initialization.md#redirecturi-considerations for more information
@bp.route("/redirect")
async def redirect():
    return ""


@bp.route("/favicon.ico")
async def favicon():
    return await bp.send_static_file("favicon.ico")


@bp.route("/assets/<path:path>")
async def assets(path):
    return await send_from_directory(Path(__file__).resolve().parent / "static" / "assets", path)


# Serve content files from blob storage from within the app to keep the example self-contained.
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@bp.route("/content/<path>")
async def content_file(path: str):
    # Remove page number from path, filename-1.txt -> filename.txt
    if path.find("#page=") > 0:
        path_parts = path.rsplit("#page=", 1)
        path = path_parts[0]
    logging.info("Opening file %s at page %s", path)
    blob_container_client = current_app.config[CONFIG_BLOB_CONTAINER_CLIENT]
    try:
        blob = await blob_container_client.get_blob_client(path).download_blob()
    except ResourceNotFoundError:
        logging.exception("Path not found: %s", path)
        abort(404)
    if not blob.properties or not blob.properties.has_key("content_settings"):
        abort(404)
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    blob_file = io.BytesIO()
    await blob.readinto(blob_file)
    blob_file.seek(0)
    return await send_file(blob_file, mimetype=mime_type, as_attachment=False, attachment_filename=path)


def error_dict(error: Exception) -> dict:
    return {"error": ERROR_MESSAGE.format(error_type=type(error))}


@bp.route("/ask", methods=["POST"])
async def ask():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    context = request_json.get("context", {})
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    context["auth_claims"] = await auth_helper.get_auth_claims_if_enabled(request.headers)
    try:
        approach = current_app.config[CONFIG_ASK_APPROACH]
        # Workaround for: https://github.com/openai/openai-python/issues/371
        async with aiohttp.ClientSession() as s:
            openai.aiosession.set(s)
            r = await approach.run(
                request_json["messages"], context=context, session_state=request_json.get("session_state")
            )
        return jsonify(r)
    except Exception as error:
        logging.exception("Exception in /ask: %s", error)
        return jsonify(error_dict(error)), 500


async def format_as_ndjson(r: AsyncGenerator[dict, None]) -> AsyncGenerator[str, None]:
    try:
        async for event in r:
            yield json.dumps(event, ensure_ascii=False) + "\n"
    except Exception as e:
        logging.exception("Exception while generating response stream: %s", e)
        yield json.dumps(error_dict(e))


@bp.route("/chat", methods=["POST"])
async def chat():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    context = request_json.get("context", {})
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    context["auth_claims"] = await auth_helper.get_auth_claims_if_enabled(request.headers)
    try:
        approach = current_app.config[CONFIG_CHAT_APPROACH]
        result = await approach.run(
            request_json["messages"],
            stream=request_json.get("stream", False),
            context=context,
            session_state=request_json.get("session_state"),
        )
        if isinstance(result, dict):
            return jsonify(result)
        else:
            response = await make_response(format_as_ndjson(result))
            response.timeout = None  # type: ignore
            return response
    except Exception as error:
        logging.exception("Exception in /chat: %s", error)
        return jsonify(error_dict(error)), 500


# Send MSAL.js settings to the client UI
@bp.route("/auth_setup", methods=["GET"])
def auth_setup():
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    return jsonify(auth_helper.get_auth_setup_for_client())


@bp.before_request
async def ensure_openai_token():
    if openai.api_type != "azure_ad":
        return
    openai_token = current_app.config[CONFIG_OPENAI_TOKEN]
    if openai_token.expires_on < time.time() + 60:
        openai_token = await current_app.config[CONFIG_CREDENTIAL].get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        current_app.config[CONFIG_OPENAI_TOKEN] = openai_token
        openai.api_key = openai_token.token


@bp.before_app_serving
async def setup_clients():
    # Replace these with your own values, either in environment variables or directly here
    AZURE_STORAGE_ACCOUNT = os.environ["AZURE_STORAGE_ACCOUNT"]
    AZURE_STORAGE_CONTAINER = os.environ["AZURE_STORAGE_CONTAINER"]
    AZURE_SEARCH_SERVICE = os.environ["AZURE_SEARCH_SERVICE"]
    AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
    # Shared by all OpenAI deployments
    OPENAI_HOST = os.getenv("OPENAI_HOST", "azure")
    OPENAI_CHATGPT_MODEL = os.environ["AZURE_OPENAI_CHATGPT_MODEL"]
    OPENAI_EMB_MODEL = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002")
    # Used with Azure OpenAI deployments
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
    # Used only with non-Azure OpenAI deployments
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")
    AZURE_USE_AUTHENTICATION = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    AZURE_SERVER_APP_ID = os.getenv("AZURE_SERVER_APP_ID")
    AZURE_SERVER_APP_SECRET = os.getenv("AZURE_SERVER_APP_SECRET")
    AZURE_CLIENT_APP_ID = os.getenv("AZURE_CLIENT_APP_ID")
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    TOKEN_CACHE_PATH = os.getenv("TOKEN_CACHE_PATH")

    KB_FIELDS_CONTENT = os.getenv("KB_FIELDS_CONTENT", "content")
    KB_FIELDS_SOURCEPAGE = os.getenv("KB_FIELDS_SOURCEPAGE", "sourcepage")

    AZURE_SEARCH_QUERY_LANGUAGE = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")
    AZURE_SEARCH_QUERY_SPELLER = os.getenv("AZURE_SEARCH_QUERY_SPELLER", "lexicon")

    # Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed,
    # just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the
    # keys for each service
    # If you encounter a blocking error during a DefaultAzureCredential resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
    azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    # Set up authentication helper
    auth_helper = AuthenticationHelper(
        use_authentication=AZURE_USE_AUTHENTICATION,
        server_app_id=AZURE_SERVER_APP_ID,
        server_app_secret=AZURE_SERVER_APP_SECRET,
        client_app_id=AZURE_CLIENT_APP_ID,
        tenant_id=AZURE_TENANT_ID,
        token_cache_path=TOKEN_CACHE_PATH,
    )

    # Set up clients for Cognitive Search and Storage
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=AZURE_SEARCH_INDEX,
        credential=azure_credential,
    )
    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", credential=azure_credential
    )
    blob_container_client = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

    # Used by the OpenAI SDK
    if OPENAI_HOST == "azure":
        openai.api_type = "azure_ad"
        openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
        openai.api_version = "2023-07-01-preview"
        openai_token = await azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
        # Store on app.config for later use inside requests
        current_app.config[CONFIG_OPENAI_TOKEN] = openai_token
    else:
        openai.api_type = "openai"
        openai.api_key = OPENAI_API_KEY
        openai.organization = OPENAI_ORGANIZATION

    current_app.config[CONFIG_CREDENTIAL] = azure_credential
    current_app.config[CONFIG_SEARCH_CLIENT] = search_client
    current_app.config[CONFIG_BLOB_CONTAINER_CLIENT] = blob_container_client
    current_app.config[CONFIG_AUTH_CLIENT] = auth_helper

    # Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
    # or some derivative, here we include several for exploration purposes
    current_app.config[CONFIG_ASK_APPROACH] = RetrieveThenReadApproach(
        search_client,
        OPENAI_HOST,
        AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        OPENAI_CHATGPT_MODEL,
        AZURE_OPENAI_EMB_DEPLOYMENT,
        OPENAI_EMB_MODEL,
        KB_FIELDS_SOURCEPAGE,
        KB_FIELDS_CONTENT,
        AZURE_SEARCH_QUERY_LANGUAGE,
        AZURE_SEARCH_QUERY_SPELLER,
    )

    current_app.config[CONFIG_CHAT_APPROACH] = ChatReadRetrieveReadApproach(
        search_client,
        OPENAI_HOST,
        AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        OPENAI_CHATGPT_MODEL,
        AZURE_OPENAI_EMB_DEPLOYMENT,
        OPENAI_EMB_MODEL,
        KB_FIELDS_SOURCEPAGE,
        KB_FIELDS_CONTENT,
        AZURE_SEARCH_QUERY_LANGUAGE,
        AZURE_SEARCH_QUERY_SPELLER,
    )


def create_app():
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor()
        AioHttpClientInstrumentor().instrument()
    app = Quart(__name__)
    app.register_blueprint(bp)
    app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)  # type: ignore[method-assign]

    # Level should be one of https://docs.python.org/3/library/logging.html#logging-levels
    default_level = "INFO"  # In development, log more verbosely
    if os.getenv("WEBSITE_HOSTNAME"):  # In production, don't log as heavily
        default_level = "WARNING"
    logging.basicConfig(level=os.getenv("APP_LOG_LEVEL", default_level))

    if allowed_origin := os.getenv("ALLOWED_ORIGIN"):
        app.logger.info("CORS enabled for %s", allowed_origin)
        cors(app, allow_origin=allowed_origin, allow_methods=["GET", "POST"])
    return app
