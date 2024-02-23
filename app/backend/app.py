import dataclasses
import io
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Union, cast
from datetime import datetime
from argparse import Namespace
from upload.prepdocs import setup_file_strategy
from upload.prepdocs import main as init_prepdocs
from upload.uploadargs import get_upload_args

import aiohttp
import aiofiles
import asyncio
import tempfile


from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from azure.keyvault.secrets.aio import SecretClient
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient, SearchIndexerClient
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
from openai import AsyncAzureOpenAI, AsyncOpenAI
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
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

from approaches.approach import Approach
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.chatreadretrievereadvision import ChatReadRetrieveReadVisionApproach
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.retrievethenreadvision import RetrieveThenReadVisionApproach
from config import (
    CONFIG_ASK_APPROACH,
    CONFIG_ASK_VISION_APPROACH,
    CONFIG_AUTH_CLIENT,
    CONFIG_BLOB_CONTAINER_CLIENT,
    CONFIG_CHAT_APPROACH,
    CONFIG_CHAT_VISION_APPROACH,
    CONFIG_GPT4V_DEPLOYED,
    CONFIG_OPENAI_CLIENT,
    CONFIG_SEARCH_CLIENT,
    CONFIG_SEMANTIC_RANKER_DEPLOYED,
    CONFIG_VECTOR_SEARCH_ENABLED,
    CONFIG_BLOB_EVALUATE_CONTAINER_CLIENT,
    CONFIG_BLOB_FEEDBACK_CONTAINER_CLIENT,
)
from core.authentication import AuthenticationHelper
from decorators import authenticated, authenticated_path
from error import error_dict, error_response

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


@bp.route("/content/<path>")
@authenticated_path
async def content_file(path: str):
    """
    Serve content files from blob storage from within the app to keep the example self-contained.
    *** NOTE *** if you are using app services authentication, this route will return unauthorized to all users that are not logged in
    if AZURE_ENFORCE_ACCESS_CONTROL is not set or false, logged in users can access all files regardless of access control
    if AZURE_ENFORCE_ACCESS_CONTROL is set to true, logged in users can only access files they have access to
    This is also slow and memory hungry.
    """
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


@bp.route("/ask", methods=["POST"])
@authenticated
async def ask(auth_claims: Dict[str, Any]):
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    context = request_json.get("context", {})
    context["auth_claims"] = auth_claims
    try:
        use_gpt4v = context.get("overrides", {}).get("use_gpt4v", False)
        approach: Approach
        if use_gpt4v and CONFIG_ASK_VISION_APPROACH in current_app.config:
            approach = cast(Approach, current_app.config[CONFIG_ASK_VISION_APPROACH])
        else:
            approach = cast(Approach, current_app.config[CONFIG_ASK_APPROACH])
        r = await approach.run(
            request_json["messages"], context=context, session_state=request_json.get("session_state")
        )
        return jsonify(r)
    except Exception as error:
        return error_response(error, "/ask")


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


async def format_as_ndjson(r: AsyncGenerator[dict, None]) -> AsyncGenerator[str, None]:
    try:
        async for event in r:
            yield json.dumps(event, ensure_ascii=False, cls=JSONEncoder) + "\n"
    except Exception as error:
        logging.exception("Exception while generating response stream: %s", error)
        yield json.dumps(error_dict(error))


@bp.route("/chat", methods=["POST"])
@authenticated
async def chat(auth_claims: Dict[str, Any]):
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    context = request_json.get("context", {})
    context["auth_claims"] = auth_claims
    try:
        use_gpt4v = context.get("overrides", {}).get("use_gpt4v", False)
        approach: Approach
        if use_gpt4v and CONFIG_CHAT_VISION_APPROACH in current_app.config:
            approach = cast(Approach, current_app.config[CONFIG_CHAT_VISION_APPROACH])
        else:
            approach = cast(Approach, current_app.config[CONFIG_CHAT_APPROACH])

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
            response.mimetype = "application/json-lines"
            return response
    except Exception as error:
        return error_response(error, "/chat")


# Send MSAL.js settings to the client UI
@bp.route("/auth_setup", methods=["GET"])
def auth_setup():
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    return jsonify(auth_helper.get_auth_setup_for_client())


@bp.route("/feedback", methods=["POST"])
async def feedback():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    feedback = json.dumps(request_json)
    try:
        blob_feedback_container_client = current_app.config[CONFIG_BLOB_FEEDBACK_CONTAINER_CLIENT]

        current_time = datetime.now()
        timestamp_str = current_time.strftime("%Y%m%d%H%M%S%f")
        filename = f"Feedback{timestamp_str}.json"

        blob = blob_feedback_container_client.get_blob_client(filename)
        await blob.upload_blob(feedback)

        return jsonify("Feedback uploaded to Blob Storage succesfully")

    except Exception as error:
        return error_response(error, "/feedback")


@bp.route("/feedback", methods=["GET"])
async def feedback_list():
    try:
        blob_feedback_container_client = current_app.config[CONFIG_BLOB_FEEDBACK_CONTAINER_CLIENT]
        blob_properties_list = blob_feedback_container_client.list_blobs(name_starts_with="Feedback")

        feedback_jsons = []
        async for blob_property in blob_properties_list:
            blob = await blob_feedback_container_client.get_blob_client(blob_property.name).download_blob()
            feedback_json = json.loads(await blob.content_as_text())
            feedback_jsons.append(feedback_json)

        return jsonify({"feedbacks": feedback_jsons})

    except Exception as error:
        return error_response(error, "/feedback")


@bp.route("/experiment_list", methods=["GET"])
async def experiment_list():
    try:
        blob_evaluate_container_client = current_app.config[CONFIG_BLOB_EVALUATE_CONTAINER_CLIENT]
        blob_properties_list = blob_evaluate_container_client.list_blobs()

        experiments_set = set()
        async for blob_property in blob_properties_list:
            folder_name = blob_property.name.split("/")[0]
            experiments_set.add(folder_name)

        result = list(experiments_set)
        result = {"experiment_names": result}
        return jsonify(result)
    except Exception as error:
        return error_response(error, "/experiment_list")


@bp.route("/experiment", methods=["GET"])
async def experiment():
    experiment_name = request.args.get("name")
    blob_evaluate_container_client = current_app.config[CONFIG_BLOB_EVALUATE_CONTAINER_CLIENT]
    try:
        result = {"eval_results": "", "evaluate_parameters": "", "summary": ""}
        for key in result.keys():
            file_name = f"{key}.json" if "eval_results" not in key else f"{key}.jsonl"
            path = f"{experiment_name}/{file_name}"
            blob = await blob_evaluate_container_client.get_blob_client(path).download_blob()
            if file_name.endswith(".jsonl"):
                json_data = [json.loads(line) for line in (await blob.content_as_text()).splitlines() if line.strip()]
            else:
                json_data = json.loads(await blob.content_as_text())
            result[key] = json_data
        return jsonify(result)
    except Exception as error:
        return error_response(error, "/experiment_list")


@bp.route("/batchevaluate", methods=["POST"])
async def batchevaluate():
    request_json = await request.get_json()
    message, _ = await start_evaluation(request_json)
    return jsonify({"status": message}), 202


async def start_evaluation(payload):
    session = aiohttp.ClientSession()
    try:
        task = asyncio.create_task(post_payload_handler(session, payload))
        return "Evaluation started, fetch /experiment_list for results", task
    except Exception as error:
        return f"Evaluation did not start, error: {error}", task


async def post_payload_handler(session, payload):
    try:
        async with session.post("https://rageval.azurewebsites.net/api/evaluate", json=payload):
            pass
    finally:
        await session.close()


@bp.route("/upload", methods=["POST"])
async def upload():
    try:
        logging.info("Uploading Files...")
        files = await request.files
        temp_dir = tempfile.TemporaryDirectory()
        temp_dir_path = Path(temp_dir.name)

        for file_key in files.keys():
            file = files[file_key]
            filename = file.filename
            temp_file_path = temp_dir_path / filename
            logging.info("Current File: %s", filename)
            file_contents = file.read()
            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                await temp_file.write(file_contents)

        args = Namespace()
        args.files = f"{str(temp_dir_path)}/*"
        args = get_upload_args(args)

        azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        ingestion_strategy = await setup_file_strategy(azure_credential, args)
        await init_prepdocs(ingestion_strategy, azure_credential, args)
        temp_dir.cleanup()
        return jsonify("File succesfully uploaded"), 202
    except Exception as error:
        logging.exception("Error", error)
        return jsonify({"error": error}), 415


@bp.route("/documents", methods=["GET"])
async def documents():
    try:
        blob_container_client = current_app.config[CONFIG_BLOB_CONTAINER_CLIENT]
        blob_properties_list = blob_container_client.list_blobs()

        documents = []
        async for blob_property in blob_properties_list:
            blob_name = blob_property.name
            documents.append(blob_name)

        print("Documents", documents)
        return jsonify({"documents": documents})

    except Exception as error:
        return error_response(error, "/documents")


@bp.route("/config", methods=["GET"])
def config():
    return jsonify(
        {
            "showGPT4VOptions": current_app.config[CONFIG_GPT4V_DEPLOYED],
            "showSemanticRankerOption": current_app.config[CONFIG_SEMANTIC_RANKER_DEPLOYED],
            "showVectorOption": current_app.config[CONFIG_VECTOR_SEARCH_ENABLED],
        }
    )


@bp.before_app_serving
async def setup_clients():
    # Replace these with your own values, either in environment variables or directly here
    AZURE_STORAGE_ACCOUNT = os.environ["AZURE_STORAGE_ACCOUNT"]
    AZURE_STORAGE_CONTAINER = os.environ["AZURE_STORAGE_CONTAINER"]
    AZURE_SEARCH_SERVICE = os.environ["AZURE_SEARCH_SERVICE"]
    AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
    SEARCH_SECRET_NAME = os.getenv("SEARCH_SECRET_NAME")
    VISION_SECRET_NAME = os.getenv("VISION_SECRET_NAME")
    AZURE_KEY_VAULT_NAME = os.getenv("AZURE_KEY_VAULT_NAME")
    # Shared by all OpenAI deployments
    OPENAI_HOST = os.getenv("OPENAI_HOST", "azure")
    OPENAI_CHATGPT_MODEL = os.environ["AZURE_OPENAI_CHATGPT_MODEL"]
    OPENAI_EMB_MODEL = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002")
    # Used with Azure OpenAI deployments
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_GPT4V_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT4V_DEPLOYMENT")
    AZURE_OPENAI_GPT4V_MODEL = os.environ.get("AZURE_OPENAI_GPT4V_MODEL")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") if OPENAI_HOST == "azure" else None
    AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT") if OPENAI_HOST == "azure" else None
    AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT", "")
    # Used only with non-Azure OpenAI deployments
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")

    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_USE_AUTHENTICATION = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    AZURE_ENFORCE_ACCESS_CONTROL = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    AZURE_SERVER_APP_ID = os.getenv("AZURE_SERVER_APP_ID")
    AZURE_SERVER_APP_SECRET = os.getenv("AZURE_SERVER_APP_SECRET")
    AZURE_CLIENT_APP_ID = os.getenv("AZURE_CLIENT_APP_ID")
    AZURE_AUTH_TENANT_ID = os.getenv("AZURE_AUTH_TENANT_ID", AZURE_TENANT_ID)

    KB_FIELDS_CONTENT = os.getenv("KB_FIELDS_CONTENT", "content")
    KB_FIELDS_SOURCEPAGE = os.getenv("KB_FIELDS_SOURCEPAGE", "sourcepage")

    AZURE_SEARCH_QUERY_LANGUAGE = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")
    AZURE_SEARCH_QUERY_SPELLER = os.getenv("AZURE_SEARCH_QUERY_SPELLER", "lexicon")
    AZURE_SEARCH_SEMANTIC_RANKER = os.getenv("AZURE_SEARCH_SEMANTIC_RANKER", "free").lower()

    USE_GPT4V = os.getenv("USE_GPT4V", "").lower() == "true"

    # Use the current user identity to authenticate with Azure OpenAI, AI Search and Blob Storage (no secrets needed,
    # just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the
    # keys for each service
    # If you encounter a blocking error during a DefaultAzureCredential resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
    azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    # Fetch any necessary secrets from Key Vault
    vision_key = None
    search_key = None
    if AZURE_KEY_VAULT_NAME and (VISION_SECRET_NAME or SEARCH_SECRET_NAME):
        key_vault_client = SecretClient(
            vault_url=f"https://{AZURE_KEY_VAULT_NAME}.vault.azure.net", credential=azure_credential
        )
        vision_key = VISION_SECRET_NAME and (await key_vault_client.get_secret(VISION_SECRET_NAME)).value
        search_key = SEARCH_SECRET_NAME and (await key_vault_client.get_secret(SEARCH_SECRET_NAME)).value
        await key_vault_client.close()

    # Set up clients for AI Search and Storage
    search_credential: Union[AsyncTokenCredential, AzureKeyCredential] = (
        AzureKeyCredential(search_key) if search_key else azure_credential
    )
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=AZURE_SEARCH_INDEX,
        credential=search_credential,
    )
    search_index_client = SearchIndexClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        credential=search_credential,
    )
    search_indexer_client = SearchIndexerClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        credential=search_credential,
    )
    print(search_indexer_client)

    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", credential=azure_credential
    )
    blob_container_client = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)
    evaluate_blob_container_client = blob_client.get_container_client("batchevaluate")
    feedback_blob_container_client = blob_client.get_container_client("feedback")

    # Set up authentication helper
    auth_helper = AuthenticationHelper(
        search_index=(await search_index_client.get_index(AZURE_SEARCH_INDEX)) if AZURE_USE_AUTHENTICATION else None,
        use_authentication=AZURE_USE_AUTHENTICATION,
        server_app_id=AZURE_SERVER_APP_ID,
        server_app_secret=AZURE_SERVER_APP_SECRET,
        client_app_id=AZURE_CLIENT_APP_ID,
        tenant_id=AZURE_AUTH_TENANT_ID,
        require_access_control=AZURE_ENFORCE_ACCESS_CONTROL,
    )

    # Used by the OpenAI SDK
    openai_client: AsyncOpenAI

    if OPENAI_HOST == "azure":
        token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
        # Store on app.config for later use inside requests
        openai_client = AsyncAzureOpenAI(
            api_version="2023-07-01-preview",
            azure_endpoint=f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com",
            azure_ad_token_provider=token_provider,
        )
    elif OPENAI_HOST == "local":
        openai_client = AsyncOpenAI(base_url=os.environ["OPENAI_BASE_URL"], api_key="no-key-required")
    else:
        openai_client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            organization=OPENAI_ORGANIZATION,
        )

    current_app.config[CONFIG_OPENAI_CLIENT] = openai_client
    current_app.config[CONFIG_SEARCH_CLIENT] = search_client
    current_app.config[CONFIG_BLOB_CONTAINER_CLIENT] = blob_container_client
    current_app.config[CONFIG_AUTH_CLIENT] = auth_helper
    current_app.config[CONFIG_BLOB_EVALUATE_CONTAINER_CLIENT] = evaluate_blob_container_client
    current_app.config[CONFIG_BLOB_FEEDBACK_CONTAINER_CLIENT] = feedback_blob_container_client

    current_app.config[CONFIG_GPT4V_DEPLOYED] = bool(USE_GPT4V)
    current_app.config[CONFIG_SEMANTIC_RANKER_DEPLOYED] = AZURE_SEARCH_SEMANTIC_RANKER != "disabled"
    current_app.config[CONFIG_VECTOR_SEARCH_ENABLED] = os.getenv("USE_VECTORS", "").lower() != "false"

    # Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
    # or some derivative, here we include several for exploration purposes
    current_app.config[CONFIG_ASK_APPROACH] = RetrieveThenReadApproach(
        search_client=search_client,
        openai_client=openai_client,
        auth_helper=auth_helper,
        chatgpt_model=OPENAI_CHATGPT_MODEL,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=OPENAI_EMB_MODEL,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
    )

    if USE_GPT4V:
        if vision_key is None:
            raise ValueError("Vision key must be set (in Key Vault) to use the vision approach.")

        current_app.config[CONFIG_ASK_VISION_APPROACH] = RetrieveThenReadVisionApproach(
            search_client=search_client,
            openai_client=openai_client,
            blob_container_client=blob_container_client,
            auth_helper=auth_helper,
            vision_endpoint=AZURE_VISION_ENDPOINT,
            vision_key=vision_key,
            gpt4v_deployment=AZURE_OPENAI_GPT4V_DEPLOYMENT,
            gpt4v_model=AZURE_OPENAI_GPT4V_MODEL,
            embedding_model=OPENAI_EMB_MODEL,
            embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
            sourcepage_field=KB_FIELDS_SOURCEPAGE,
            content_field=KB_FIELDS_CONTENT,
            query_language=AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=AZURE_SEARCH_QUERY_SPELLER,
        )

        current_app.config[CONFIG_CHAT_VISION_APPROACH] = ChatReadRetrieveReadVisionApproach(
            search_client=search_client,
            openai_client=openai_client,
            blob_container_client=blob_container_client,
            auth_helper=auth_helper,
            vision_endpoint=AZURE_VISION_ENDPOINT,
            vision_key=vision_key,
            gpt4v_deployment=AZURE_OPENAI_GPT4V_DEPLOYMENT,
            gpt4v_model=AZURE_OPENAI_GPT4V_MODEL,
            embedding_model=OPENAI_EMB_MODEL,
            embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
            sourcepage_field=KB_FIELDS_SOURCEPAGE,
            content_field=KB_FIELDS_CONTENT,
            query_language=AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=AZURE_SEARCH_QUERY_SPELLER,
        )

    current_app.config[CONFIG_CHAT_APPROACH] = ChatReadRetrieveReadApproach(
        search_client=search_client,
        openai_client=openai_client,
        auth_helper=auth_helper,
        chatgpt_model=OPENAI_CHATGPT_MODEL,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=OPENAI_EMB_MODEL,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
    )


@bp.after_app_serving
async def close_clients():
    await current_app.config[CONFIG_SEARCH_CLIENT].close()
    await current_app.config[CONFIG_BLOB_CONTAINER_CLIENT].close()


def create_app():
    app = Quart(__name__)
    app.register_blueprint(bp)

    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor()
        # This tracks HTTP requests made by aiohttp:
        AioHttpClientInstrumentor().instrument()
        # This tracks HTTP requests made by httpx/openai:
        HTTPXClientInstrumentor().instrument()
        # This middleware tracks app route requests:
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
