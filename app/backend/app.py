import dataclasses
import io
import json
import logging
import mimetypes
import os
import time
from datetime import datetime
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Union, cast

from azure.cognitiveservices.speech import (
    ResultReason,
    SpeechConfig,
    SpeechSynthesisOutputFormat,
    SpeechSynthesisResult,
    SpeechSynthesizer,
)
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import (
    AzureDeveloperCliCredential,
    ManagedIdentityCredential,
    ClientSecretCredential,
    get_bearer_token_provider,
)
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.search.documents.agent.aio import KnowledgeAgentRetrievalClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.storage.blob.aio import ContainerClient
from azure.storage.blob.aio import StorageStreamDownloader as BlobDownloader
from azure.storage.filedatalake.aio import FileSystemClient
from azure.storage.filedatalake.aio import StorageStreamDownloader as DatalakeDownloader
from openai import AsyncAzureOpenAI, AsyncOpenAI
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.httpx import (
    HTTPXClientInstrumentor,
)
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
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
from approaches.promptmanager import PromptyManager
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.retrievethenreadvision import RetrieveThenReadVisionApproach
from chat_history.cosmosdb import chat_history_cosmosdb_bp
from config import (
    CONFIG_AGENT_CLIENT,
    CONFIG_AGENTIC_RETRIEVAL_ENABLED,
    CONFIG_ASK_APPROACH,
    CONFIG_ASK_VISION_APPROACH,
    CONFIG_AUTH_CLIENT,
    CONFIG_BLOB_CONTAINER_CLIENT,
    CONFIG_CHAT_APPROACH,
    CONFIG_CHAT_HISTORY_BROWSER_ENABLED,
    CONFIG_CHAT_HISTORY_COSMOS_ENABLED,
    CONFIG_CHAT_VISION_APPROACH,
    CONFIG_CREDENTIAL,
    CONFIG_DEFAULT_REASONING_EFFORT,
    CONFIG_GPT4V_DEPLOYED,
    CONFIG_INGESTER,
    CONFIG_LANGUAGE_PICKER_ENABLED,
    CONFIG_OPENAI_CLIENT,
    CONFIG_QUERY_REWRITING_ENABLED,
    CONFIG_REASONING_EFFORT_ENABLED,
    CONFIG_SEARCH_CLIENT,
    CONFIG_SEMANTIC_RANKER_DEPLOYED,
    CONFIG_SPEECH_INPUT_ENABLED,
    CONFIG_SPEECH_OUTPUT_AZURE_ENABLED,
    CONFIG_SPEECH_OUTPUT_BROWSER_ENABLED,
    CONFIG_SPEECH_SERVICE_ID,
    CONFIG_SPEECH_SERVICE_LOCATION,
    CONFIG_SPEECH_SERVICE_TOKEN,
    CONFIG_SPEECH_SERVICE_VOICE,
    CONFIG_SHAREPOINT_BASE_URL,
    CONFIG_STREAMING_ENABLED,
    CONFIG_USER_BLOB_CONTAINER_CLIENT,
    CONFIG_USER_UPLOAD_ENABLED,
    CONFIG_VECTOR_SEARCH_ENABLED,
)
from core.authentication import AuthenticationHelper
from core.init_bot import init_bot_context, validate_runtime_status
from core.sessionhelper import create_session_id
from decorators import authenticated, authenticated_path
from error import error_dict, error_response
from prepdocs import (
    clean_key_if_exists,
    setup_embeddings_service,
    setup_file_processors,
    setup_search_info,
)
from prepdocslib.filestrategy import UploadUserFileStrategy
from prepdocslib.listfilestrategy import File

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
async def content_file(path: str, auth_claims: dict[str, Any]):
    """
    Serve content files from blob storage from within the app to keep the example self-contained.
    *** NOTE *** if you are using app services authentication, this route will return unauthorized to all users that are not logged in
    if AZURE_ENFORCE_ACCESS_CONTROL is not set or false, logged in users can access all files regardless of access control
    if AZURE_ENFORCE_ACCESS_CONTROL is set to true, logged in users can only access files they have access to
    This is also slow and memory hungry.
    """
    # Remove page number from path, filename-1.txt -> filename.txt
    # This shouldn't typically be necessary as browsers don't send hash fragments to servers
    if path.find("#page=") > 0:
        path_parts = path.rsplit("#page=", 1)
        path = path_parts[0]
    current_app.logger.info("Opening file %s", path)
    blob_container_client: ContainerClient = current_app.config[CONFIG_BLOB_CONTAINER_CLIENT]
    blob: Union[BlobDownloader, DatalakeDownloader]
    try:
        blob = await blob_container_client.get_blob_client(path).download_blob()
    except ResourceNotFoundError:
        current_app.logger.info("Path not found in general Blob container: %s", path)
        if current_app.config[CONFIG_USER_UPLOAD_ENABLED]:
            try:
                user_oid = auth_claims["oid"]
                user_blob_container_client = current_app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT]
                user_directory_client: FileSystemClient = user_blob_container_client.get_directory_client(user_oid)
                file_client = user_directory_client.get_file_client(path)
                blob = await file_client.download_file()
            except ResourceNotFoundError:
                current_app.logger.exception("Path not found in DataLake: %s", path)
                abort(404)
        else:
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
async def ask(auth_claims: dict[str, Any]):
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
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
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
async def chat(auth_claims: dict[str, Any]):
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

        # If session state is provided, persists the session state,
        # else creates a new session_id depending on the chat history options enabled.
        session_state = request_json.get("session_state")
        if session_state is None:
            session_state = create_session_id(
                current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED],
                current_app.config[CONFIG_CHAT_HISTORY_BROWSER_ENABLED],
            )
        result = await approach.run(
            request_json["messages"],
            context=context,
            session_state=session_state,
        )
        return jsonify(result)
    except Exception as error:
        return error_response(error, "/chat")


@bp.route("/chat/stream", methods=["POST"])
@authenticated
async def chat_stream(auth_claims: dict[str, Any]):
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

        # If session state is provided, persists the session state,
        # else creates a new session_id depending on the chat history options enabled.
        session_state = request_json.get("session_state")
        if session_state is None:
            session_state = create_session_id(
                current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED],
                current_app.config[CONFIG_CHAT_HISTORY_BROWSER_ENABLED],
            )
        result = await approach.run_stream(
            request_json["messages"],
            context=context,
            session_state=session_state,
        )
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


@bp.route("/config", methods=["GET"])
def config():
    return jsonify(
        {
            "showGPT4VOptions": current_app.config[CONFIG_GPT4V_DEPLOYED],
            "showSemanticRankerOption": current_app.config[CONFIG_SEMANTIC_RANKER_DEPLOYED],
            "showQueryRewritingOption": current_app.config[CONFIG_QUERY_REWRITING_ENABLED],
            "showReasoningEffortOption": current_app.config[CONFIG_REASONING_EFFORT_ENABLED],
            "streamingEnabled": current_app.config[CONFIG_STREAMING_ENABLED],
            "defaultReasoningEffort": current_app.config[CONFIG_DEFAULT_REASONING_EFFORT],
            "showVectorOption": current_app.config[CONFIG_VECTOR_SEARCH_ENABLED],
            "showUserUpload": current_app.config[CONFIG_USER_UPLOAD_ENABLED],
            "showLanguagePicker": current_app.config[CONFIG_LANGUAGE_PICKER_ENABLED],
            "showSpeechInput": current_app.config[CONFIG_SPEECH_INPUT_ENABLED],
            "showSpeechOutputBrowser": current_app.config[CONFIG_SPEECH_OUTPUT_BROWSER_ENABLED],
            "showSpeechOutputAzure": current_app.config[CONFIG_SPEECH_OUTPUT_AZURE_ENABLED],
            "showChatHistoryBrowser": current_app.config[CONFIG_CHAT_HISTORY_BROWSER_ENABLED],
            "showChatHistoryCosmos": current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED],
            "showAgenticRetrievalOption": current_app.config[CONFIG_AGENTIC_RETRIEVAL_ENABLED],
            "sharePointBaseUrl": current_app.config.get(CONFIG_SHAREPOINT_BASE_URL, "https://lumston.sharepoint.com/sites/AIBotProjectAutomation"),
        }
    )


@bp.route("/speech", methods=["POST"])
async def speech():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415

    speech_token = current_app.config.get(CONFIG_SPEECH_SERVICE_TOKEN)
    if speech_token is None or speech_token.expires_on < time.time() + 60:
        speech_token = await current_app.config[CONFIG_CREDENTIAL].get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        current_app.config[CONFIG_SPEECH_SERVICE_TOKEN] = speech_token

    request_json = await request.get_json()
    text = request_json["text"]
    try:
        # Construct a token as described in documentation:
        # https://learn.microsoft.com/azure/ai-services/speech-service/how-to-configure-azure-ad-auth?pivots=programming-language-python
        auth_token = (
            "aad#"
            + current_app.config[CONFIG_SPEECH_SERVICE_ID]
            + "#"
            + current_app.config[CONFIG_SPEECH_SERVICE_TOKEN].token
        )
        speech_config = SpeechConfig(auth_token=auth_token, region=current_app.config[CONFIG_SPEECH_SERVICE_LOCATION])
        speech_config.speech_synthesis_voice_name = current_app.config[CONFIG_SPEECH_SERVICE_VOICE]
        speech_config.speech_synthesis_output_format = SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        result: SpeechSynthesisResult = synthesizer.speak_text_async(text).get()
        if result.reason == ResultReason.SynthesizingAudioCompleted:
            return result.audio_data, 200, {"Content-Type": "audio/mp3"}
        elif result.reason == ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            current_app.logger.error(
                "Speech synthesis canceled: %s %s", cancellation_details.reason, cancellation_details.error_details
            )
            raise Exception("Speech synthesis canceled. Check logs for details.")
        else:
            current_app.logger.error("Unexpected result reason: %s", result.reason)
            raise Exception("Speech synthesis failed. Check logs for details.")
    except Exception as e:
        current_app.logger.exception("Exception in /speech")
        return jsonify({"error": str(e)}), 500


@bp.post("/upload")
@authenticated
async def upload(auth_claims: dict[str, Any]):
    request_files = await request.files
    if "file" not in request_files:
        # If no files were included in the request, return an error response
        return jsonify({"message": "No file part in the request", "status": "failed"}), 400

    user_oid = auth_claims["oid"]
    file = request_files.getlist("file")[0]
    user_blob_container_client: FileSystemClient = current_app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT]
    user_directory_client = user_blob_container_client.get_directory_client(user_oid)
    try:
        await user_directory_client.get_directory_properties()
    except ResourceNotFoundError:
        current_app.logger.info("Creating directory for user %s", user_oid)
        await user_directory_client.create_directory()
    await user_directory_client.set_access_control(owner=user_oid)
    file_client = user_directory_client.get_file_client(file.filename)
    file_io = file
    file_io.name = file.filename
    file_io = io.BufferedReader(file_io)
    await file_client.upload_data(file_io, overwrite=True, metadata={"UploadedBy": user_oid})
    file_io.seek(0)
    ingester: UploadUserFileStrategy = current_app.config[CONFIG_INGESTER]
    await ingester.add_file(File(content=file_io, acls={"oids": [user_oid]}, url=file_client.url))
    return jsonify({"message": "File uploaded successfully"}), 200


@bp.post("/delete_uploaded")
@authenticated
async def delete_uploaded(auth_claims: dict[str, Any]):
    request_json = await request.get_json()
    filename = request_json.get("filename")
    user_oid = auth_claims["oid"]
    user_blob_container_client: FileSystemClient = current_app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT]
    user_directory_client = user_blob_container_client.get_directory_client(user_oid)
    file_client = user_directory_client.get_file_client(filename)
    await file_client.delete_file()
    ingester = current_app.config[CONFIG_INGESTER]
    await ingester.remove_file(filename, user_oid)
    return jsonify({"message": f"File {filename} deleted successfully"}), 200


@bp.get("/list_uploaded")
@authenticated
async def list_uploaded(auth_claims: dict[str, Any]):
    user_oid = auth_claims["oid"]
    user_blob_container_client: FileSystemClient = current_app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT]
    files = []
    try:
        all_paths = user_blob_container_client.get_paths(path=user_oid)
        async for path in all_paths:
            files.append(path.name.split("/", 1)[1])
    except ResourceNotFoundError as error:
        if error.status_code != 404:
            current_app.logger.exception("Error listing uploaded files", error)
    return jsonify(files), 200


@bp.route("/debug/sharepoint", methods=["GET"])
async def debug_sharepoint():
    """Endpoint de debug para probar la conectividad con SharePoint"""
    try:
        from core.graph import GraphClient

        graph_client = GraphClient()
        # Usar el método existente para buscar archivos de pilotos
        pilotos_files = graph_client.search_files_in_pilotos_folder()

        return jsonify(
            {
                "status": "success",
                "data": {
                    "success": True,
                    "message": f"Encontrados {len(pilotos_files)} archivos de pilotos",
                    "files_count": len(pilotos_files),
                    "files": pilotos_files[:5] if pilotos_files else []  # Solo los primeros 5 para debug
                },
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error en debug_sharepoint: {e}")
        return jsonify(
            {
                "status": "error",
                "error": str(e),
                "debug_info": "Check logs for detailed error information"
            }
        )

@bp.route("/debug/sharepoint/sites", methods=["GET"])
async def debug_sharepoint_sites():
    """Endpoint para ver todos los sitios de SharePoint disponibles"""
    try:
        from core.graph import GraphClient

        graph_client = GraphClient()
        sites = graph_client.get_sharepoint_sites()

        return jsonify(
            {
                "status": "success",
                "data": {
                    "sites_count": len(sites),
                    "sites": [
                        {
                            "id": site.get("id"),
                            "displayName": site.get("displayName"),
                            "webUrl": site.get("webUrl"),
                            "isTeamSite": site.get("isTeamSite", False)
                        }
                        for site in sites
                    ]
                }
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error en debug_sharepoint_sites: {e}")
        return jsonify(
            {
                "status": "error",
                "error": str(e),
            }
        ), 500


@bp.route("/debug/logs", methods=["GET"])
async def debug_logs():
    """Endpoint para ver logs recientes del sistema"""
    try:
        import logging
        
        # Obtener el último handler de logs
        logger = logging.getLogger()
        
        return jsonify(
            {
                "status": "success",
                "data": {
                    "log_level": logging.getLevelName(logger.level),
                    "handlers_count": len(logger.handlers),
                    "message": "Logs están siendo escritos en terminal. Para ver logs detallados, revisa el terminal donde está corriendo el bot."
                }
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error en debug_logs: {e}")
        return jsonify(
            {
                "status": "error",
                "error": str(e),
            }
        ), 500


@bp.route("/debug/pilot-query", methods=["POST"])
async def debug_pilot_query():
    """Endpoint de debug para probar detección de consultas relacionadas con pilotos"""
    try:
        if not request.is_json:
            return jsonify({"error": "request must be json"}), 415

        request_json = await request.get_json()
        query = request_json.get("query", "")

        if not query:
            return jsonify({"error": "query is required"}), 400

        # Obtener la instancia del chat approach
        from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach

        chat_approach = current_app.config[CONFIG_CHAT_APPROACH]
        if isinstance(chat_approach, ChatReadRetrieveReadApproach):
            is_pilot_related = chat_approach._is_pilot_related_query(query)

            # También probar la búsqueda en SharePoint si es relacionada con pilotos
            sharepoint_results = []
            if is_pilot_related:
                sharepoint_results = await chat_approach._search_sharepoint_files(query, top=1)

            return jsonify(
                {
                    "query": query,
                    "is_pilot_related": is_pilot_related,
                    "sharepoint_results_count": len(sharepoint_results),
                    "sharepoint_results": sharepoint_results[:2],  # Solo mostrar los primeros 2 para debug
                }
            )
        else:
            return jsonify({"error": "Chat approach not configured correctly"}), 500

    except Exception as e:
        current_app.logger.error(f"Error en debug_pilot_query: {e}")
        return jsonify(
            {
                "error": str(e),
            }
        ), 500


@bp.route("/debug")
async def debug_page():
    """Página de debug para probar funcionalidad de SharePoint"""
    return await send_from_directory("../frontend", "debug-sharepoint.html")


@bp.route("/debug/managed-identity", methods=["GET"])
async def debug_managed_identity():
    """Endpoint para diagnosticar el Managed Identity desde el Container App"""
    try:
        from azure.identity.aio import ManagedIdentityCredential
        from azure.core.exceptions import ClientAuthenticationError
        
        # Función auxiliar para validar acceso
        async def validate_mi_access(resource: str):
            try:
                credential = ManagedIdentityCredential()
                token = await credential.get_token(resource)
                return {
                    "resource": resource,
                    "status": "success",
                    "token_length": len(token.token) if token.token else 0,
                    "expires_on": token.expires_on if hasattr(token, 'expires_on') else None
                }
            except ClientAuthenticationError as e:
                return {
                    "resource": resource,
                    "status": "auth_error",
                    "error": str(e)
                }
            except Exception as e:
                return {
                    "resource": resource,
                    "status": "error",
                    "error": str(e)
                }
        
        # Recursos a probar
        resources_to_test = [
            "https://search.azure.com/",  # Azure Search scope
            "https://management.azure.com/",  # Azure Management scope
            "https://cognitiveservices.azure.com/",  # Cognitive Services
        ]
        
        results = []
        for resource in resources_to_test:
            result = await validate_mi_access(resource)
            results.append(result)
        
        # Información adicional del entorno
        env_info = {
            "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", "No configurado"),
            "RUNNING_IN_PRODUCTION": os.getenv("RUNNING_IN_PRODUCTION", "No configurado"),
            "WEBSITE_HOSTNAME": os.getenv("WEBSITE_HOSTNAME", "No configurado"),
            "MSI_ENDPOINT": os.getenv("MSI_ENDPOINT", "No configurado"),
            "IDENTITY_ENDPOINT": os.getenv("IDENTITY_ENDPOINT", "No configurado"),
        }
        
        return jsonify({
            "status": "success",
            "managed_identity_tests": results,
            "environment_info": env_info,
            "summary": {
                "total_tests": len(results),
                "successful": len([r for r in results if r["status"] == "success"]),
                "failed": len([r for r in results if r["status"] != "success"])
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en debug de Managed Identity: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "Error al validar Managed Identity"
        }), 500


@bp.route("/debug/search-validation", methods=["GET"])
async def debug_search_validation():
    """Endpoint para validar completamente el acceso a Azure Search"""
    try:
        from healthchecks.search import (
            validate_search_environment_vars, 
            validate_search_credential_scope, 
            validate_search_access
        )
        
        current_app.logger.info("🔍 Iniciando validación completa de Azure Search...")
        
        # Paso 1: Validar variables de entorno
        env_check = validate_search_environment_vars()
        if env_check["status"] == "error":
            return jsonify({
                "status": "error",
                "step": "environment_variables",
                "error": "Variables de entorno faltantes",
                "details": env_check
            }), 500
        
        # Paso 2: Obtener credencial actual
        azure_credential = current_app.config[CONFIG_CREDENTIAL]
        
        # Paso 3: Validar scope de la credencial
        current_app.logger.info("🔑 Validando scope de credencial...")
        scope_valid = await validate_search_credential_scope(azure_credential)
        
        if not scope_valid:
            return jsonify({
                "status": "error",
                "step": "credential_scope",
                "error": "Credencial no puede obtener tokens para Azure Search",
                "environment_check": env_check
            }), 500
        
        # Paso 4: Validar acceso completo a Azure Search
        endpoint = env_check["endpoint"]
        index_name = env_check["required_vars"]["AZURE_SEARCH_INDEX"]
        
        current_app.logger.info(f"🌐 Validando acceso a {endpoint} con índice {index_name}...")
        access_valid = await validate_search_access(endpoint, azure_credential, index_name)
        
        if access_valid:
            return jsonify({
                "status": "success",
                "message": "✅ Todas las validaciones de Azure Search pasaron exitosamente",
                "environment_check": env_check,
                "credential_scope": "valid",
                "search_access": "valid",
                "recommendations": [
                    "Azure Search está configurado correctamente",
                    "Managed Identity tiene los permisos necesarios",
                    "El endpoint y el índice son accesibles"
                ]
            })
        else:
            return jsonify({
                "status": "error",
                "step": "search_access",
                "error": "No se pudo acceder a Azure Search",
                "environment_check": env_check,
                "credential_scope": "valid",
                "search_access": "failed",
                "recommendations": [
                    "Verifica los roles RBAC en Azure Search",
                    "Asegúrate que el Container App tenga System-Assigned Managed Identity",
                    "Roles necesarios: Search Index Data Reader, Search Service Contributor, Search Index Data Contributor"
                ]
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error en validación de Azure Search: {str(e)}")
        return jsonify({
            "status": "error",
            "step": "unexpected_error",
            "error": str(e),
            "message": "Error inesperado durante la validación"
        }), 500


@bp.route("/debug/search-detailed", methods=["GET"])
async def debug_search_detailed():
    """Diagnóstico detallado de Azure Search ejecutando script especializado"""
    import subprocess
    import sys
    import os
    
    try:
        # Ejecutar el script de diagnóstico detallado
        script_path = os.path.join(os.path.dirname(__file__), "debug_search_access.py")
        
        # Ejecutar el script y capturar output
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__),
            env=os.environ.copy(),
            timeout=30  # 30 second timeout
        )
        
        return jsonify({
            "status": "completed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "diagnostic_summary": {
                "rbac_validation": "✅" if "Estado RBAC: success" in result.stdout else "❌",
                "credentials_test": "✅" if "✅ Token obtenido" in result.stdout else "❌",
                "rest_api_test": "✅" if "✅ Acceso exitoso a Azure Search" in result.stdout else "❌", 
                "search_client_test": "✅" if "✅ SearchClient funcionando" in result.stdout else "❌"
            }
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "timeout",
            "error": "El diagnóstico excedió el tiempo límite de 30 segundos"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        })


@bp.route("/debug/rbac-status", methods=["GET"])
async def debug_rbac_status():
    """Endpoint específico para consultar el estado RBAC de Azure Search"""
    try:
        from healthchecks.rbac_validation import get_rbac_status_dict
        
        # Obtener estado RBAC
        rbac_status = await get_rbac_status_dict()
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "rbac_status": rbac_status,
            "recommendations": [] if rbac_status.get("rbac_validation") == "success" else [
                "Verifica que el Managed Identity del Container App tenga los roles necesarios",
                "Roles requeridos: Search Index Data Reader, Search Index Data Contributor, Search Service Contributor",
                "Usa Azure Portal > Azure Search > Access Control (IAM) para asignar roles"
            ]
        })
        
    except ImportError:
        return jsonify({
            "status": "error",
            "error": "Módulo rbac_validation no disponible",
            "solution": "Asegúrate de que healthchecks/rbac_validation.py esté en el contenedor"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@bp.route("/debug/sharepoint/explore", methods=["GET"])
async def debug_sharepoint_explore():
    """Endpoint de debug para explorar la estructura de SharePoint"""
    try:
        from core.graph import GraphClient

        graph_client = GraphClient()
        site_name = request.args.get('site_name', 'Software engineering')
        site_url = request.args.get('site_url', '')
        
        # Buscar el sitio por nombre o URL
        site = None
        if site_url:
            current_app.logger.info(f"Buscando sitio por URL: {site_url}")
            site = graph_client.find_site_by_url(site_url)
        
        if not site:
            current_app.logger.info(f"Buscando sitio por nombre: {site_name}")
            site = graph_client.find_site_by_name(site_name)
        
        if not site:
            return jsonify({
                "status": "error",
                "error": f"No se encontró el sitio: {site_name}",
                "available_sites": [
                    {
                        "name": s.get("displayName", ""),
                        "webUrl": s.get("webUrl", ""),
                        "isTeamSite": s.get("isTeamSite", False),
                        "teamDisplayName": s.get("teamDisplayName", "")
                    }
                    for s in graph_client.get_sharepoint_sites()
                ]
            }), 404
        
        # Explorar la estructura del sitio
        site_id = site["id"]
        
        # Obtener elementos de la raíz
        root_items = graph_client.get_drive_items(site_id)
        
        # Buscar la carpeta Pilotos recursivamente
        pilotos_path = graph_client.find_pilotos_folder_recursive(site_id)
        
        return jsonify({
            "status": "success",
            "site_info": {
                "id": site["id"],
                "name": site.get("displayName", ""),
                "webUrl": site.get("webUrl", ""),
                "isTeamSite": site.get("isTeamSite", False),
                "teamDisplayName": site.get("teamDisplayName", "")
            },
            "root_items": [
                {
                    "name": item.get("name", ""),
                    "type": "folder" if "folder" in item else "file",
                    "id": item.get("id", "")
                }
                for item in root_items[:10]  # Limitar a 10 elementos
            ],
            "pilotos_folder_path": pilotos_path,
            "total_root_items": len(root_items)
        })

    except Exception as e:
        current_app.logger.error(f"Error en debug_sharepoint_explore: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@bp.route("/debug/sharepoint/search-folders", methods=["GET"])
async def debug_sharepoint_search_folders():
    """Endpoint de debug para buscar carpetas específicas en SharePoint"""
    try:
        from core.graph import GraphClient

        graph_client = GraphClient()
        site_url = request.args.get('site_url', 'https://lumston.sharepoint.com/sites/AIBotProjectAutomation/')
        search_term = request.args.get('search_term', 'volaris')
        
        # Buscar el sitio por URL
        site = graph_client.find_site_by_url(site_url)
        if not site:
            return jsonify({
                "status": "error",
                "error": f"No se encontró el sitio: {site_url}"
            }), 404
        
        site_id = site["id"]
        
        # Obtener TODOS los elementos de la raíz
        all_root_items = graph_client.get_drive_items(site_id)
        
        # Buscar carpetas que contengan el término de búsqueda
        matching_folders = []
        for item in all_root_items:
            if "folder" in item:
                item_name = item.get("name", "").lower()
                if (search_term.lower() in item_name or 
                    "volaris" in item_name or 
                    "flightbot" in item_name or
                    "pilot" in item_name):
                    matching_folders.append({
                        "name": item.get("name", ""),
                        "id": item.get("id", ""),
                        "webUrl": item.get("webUrl", "")
                    })
        
        return jsonify({
            "status": "success",
            "site_info": {
                "id": site["id"],
                "name": site.get("displayName", ""),
                "webUrl": site.get("webUrl", "")
            },
            "search_term": search_term,
            "total_root_items": len(all_root_items),
            "matching_folders": matching_folders,
            "all_folder_names": [item.get("name", "") for item in all_root_items if "folder" in item][:50]  # Mostrar primeros 50 nombres de carpetas
        })

    except Exception as e:
        current_app.logger.error(f"Error en debug_sharepoint_search_folders: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@bp.route("/debug/sharepoint/library", methods=["GET"])
async def debug_sharepoint_library():
    """Endpoint de debug para explorar la biblioteca de documentos de SharePoint"""
    try:
        from core.graph import GraphClient

        graph_client = GraphClient()
        site_url = "https://lumston.sharepoint.com/sites/AIBotProjectAutomation/"
        
        # Buscar el sitio por URL
        site = graph_client.find_site_by_url(site_url)
        if not site:
            return jsonify({
                "status": "error",
                "error": f"No se encontró el sitio: {site_url}"
            }), 404
        
        site_id = site["id"]
        
        # Obtener elementos de la biblioteca de documentos
        library_items = graph_client.get_document_library_items(site_id)
        
        # Buscar la carpeta Pilotos en la biblioteca
        pilotos_path = graph_client.find_pilotos_in_document_library(site_id)
        
        # Filtrar solo carpetas para mostrar la estructura
        folders = []
        for item in library_items:
            fields = item.get("fields", {})
            content_type = fields.get("ContentType", "")
            file_leaf_ref = fields.get("FileLeafRef", "")
            file_ref = fields.get("FileRef", "")
            
            if "folder" in content_type.lower():
                folders.append({
                    "name": file_leaf_ref,
                    "path": file_ref,
                    "contentType": content_type
                })
        
        return jsonify({
            "status": "success",
            "site_info": {
                "id": site["id"],
                "name": site.get("displayName", ""),
                "webUrl": site.get("webUrl", "")
            },
            "total_library_items": len(library_items),
            "folders_count": len(folders),
            "folders": folders[:20],  # Mostrar primeras 20 carpetas
            "pilotos_folder_path": pilotos_path
        })

    except Exception as e:
        current_app.logger.error(f"Error en debug_sharepoint_library: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@bp.route("/debug/sharepoint/search", methods=["GET"])
async def debug_sharepoint_search():
    """Endpoint de debug para buscar archivos por contenido en SharePoint"""
    try:
        from core.graph import GraphClient

        graph_client = GraphClient()
        site_url = "https://lumston.sharepoint.com/sites/AIBotProjectAutomation/"
        search_query = request.args.get('query', 'pilotos')
        
        # Buscar el sitio por URL
        site = graph_client.find_site_by_url(site_url)
        if not site:
            return jsonify({
                "status": "error",
                "error": f"No se encontró el sitio: {site_url}"
            }), 404
        
        site_id = site["id"]
        
        # Buscar archivos por contenido
        files = graph_client.search_all_files_in_site(site_id, search_query)
        
        # También obtener información de los drives
        drives = graph_client.get_all_drives_in_site(site_id)
        
        return jsonify({
            "status": "success",
            "site_info": {
                "id": site["id"],
                "name": site.get("displayName", ""),
                "webUrl": site.get("webUrl", "")
            },
            "search_query": search_query,
            "files_found": len(files),
            "files": files[:25],  # Mostrar primeros 25 archivos
            "drives": drives
        })

    except Exception as e:
        current_app.logger.error(f"Error en debug_sharepoint_search: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@bp.route("/debug/sharepoint/config", methods=["GET"])
async def debug_sharepoint_config():
    """Endpoint para verificar la configuración actual de SharePoint"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from core.graph import get_sharepoint_config_summary
        config = get_sharepoint_config_summary()
        
        return {
            "config": config,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error obteniendo configuración SharePoint: {e}")
        return {"error": str(e), "status": "error"}, 500

@bp.route("/debug/sharepoint/test-configured-folders", methods=["GET"])
async def debug_test_configured_folders():
    """Endpoint para probar búsqueda con carpetas configuradas"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from core.graph import get_configured_files
        
        files = get_configured_files()
        
        return {
            "files_found": len(files),
            "found_files": files[:25],  # Mostrar solo primeros 25 para evitar sobrecarga
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error probando carpetas configuradas: {e}")
        return {"error": str(e), "status": "error"}, 500

@bp.route("/debug/sharepoint/aibot-site", methods=["GET"])
async def debug_aibot_site():
    """Debug específico para el sitio AI Volaris Cognitive Chatbot"""
    try:
        from core.graph import GraphClient
        
        graph_client = GraphClient()
        
        # Buscar el sitio específico
        site = graph_client.find_site_by_name("AI Volaris Cognitive Chatbot")
        if not site:
            return jsonify({
                "status": "error", 
                "message": "Sitio AI Volaris Cognitive Chatbot no encontrado"
            })
        
        site_id = site["id"]
        site_name = site.get("displayName", "Unknown")
        
        # Obtener la estructura de bibliotecas de documentos
        document_libraries = graph_client.get_document_library_items(site_id)
        
        # Buscar carpetas que contengan "piloto", "flightbot", "documentos"
        relevant_folders = []
        for item in document_libraries[:50]:  # Limitar a 50 elementos
            fields = item.get("fields", {})
            content_type = fields.get("ContentType", "")
            file_leaf_ref = fields.get("FileLeafRef", "")
            file_ref = fields.get("FileRef", "")
            
            if ("folder" in content_type.lower() and 
                any(keyword in file_leaf_ref.lower() for keyword in ["piloto", "flightbot", "documentos", "compartidos", "shared"])):
                relevant_folders.append({
                    "name": file_leaf_ref,
                    "path": file_ref,
                    "content_type": content_type
                })
        
        # Buscar archivos usando búsqueda de contenido
        content_search_files = graph_client.search_all_files_in_site(site_id, "pilotos")
        
        return jsonify({
            "status": "success",
            "site_info": {
                "name": site_name,
                "id": site_id,
                "url": site.get("webUrl", "")
            },
            "document_library_items": len(document_libraries),
            "relevant_folders": relevant_folders,
            "content_search_results": len(content_search_files),
            "sample_content_files": content_search_files[:5] if content_search_files else []
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en debug_aibot_site: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

@bp.route("/debug/sharepoint/pilotos-direct", methods=["GET"])
async def debug_pilotos_direct():
    """Debug endpoint para acceso directo a carpeta 'Documentos Flightbot / PILOTOS'"""
    try:
        from core.graph import get_pilotos_files_direct
        
        current_app.logger.info("Probando acceso directo a carpeta de pilotos...")
        
        files = get_pilotos_files_direct()
        
        return jsonify({
            "status": "success",
            "method": "direct_access",
            "total_files": len(files),
            "files": files[:25] if files else [],  # Primeros 25 archivos
            "sample_file_names": [f["name"] for f in files[:25]] if files else []
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en debug_pilotos_direct: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })

async def debug_find_specific_file():
    """Debug endpoint para buscar un archivo específico en todos los sitios de SharePoint"""
    try:
        from core.graph import GraphClient
        
        filename = request.args.get('filename', '20051222 AIP AD 1.1-1 Introducción.pdf')
        graph_client = GraphClient()
        
        current_app.logger.info(f"Buscando archivo: {filename}")
        
        # Obtener todos los sitios de SharePoint
        sites = graph_client.get_sharepoint_sites()
        current_app.logger.info(f"Explorando {len(sites)} sitios de SharePoint")
        
        found_files = []
        
        for site in sites[:20]:  # Limitar a primeros 20 sitios para evitar timeout
            try:
                site_id = site["id"]
                site_name = site.get("displayName", site.get("name", "Unknown"))
                current_app.logger.info(f"Buscando en sitio: {site_name}")
                
                # Buscar archivos en este sitio
                files = graph_client.search_all_files_in_site(site_id, filename.split('.')[0])  # Buscar por parte del nombre
                
                for file in files:
                    if filename.lower() in file.get("name", "").lower():
                        found_files.append({
                            "site_name": site_name,
                            "site_id": site_id,
                            "site_url": site.get("webUrl", ""),
                            "file": file
                        })
                        current_app.logger.info(f"¡Archivo encontrado en {site_name}!")
                        
            except Exception as e:
                current_app.logger.warning(f"Error buscando en sitio {site_name}: {e}")
                continue
        
        return jsonify({
            "status": "success",
            "filename_searched": filename,
            "sites_explored": len(sites),
            "files_found": len(found_files),
            "found_files": found_files
        })

    except Exception as e:
        current_app.logger.error(f"Error en debug_find_specific_file: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@bp.route("/health/full-checklist", methods=["GET"])
async def health_full_checklist():
    """
    Endpoint de health check que ejecuta el checklist completo
    Se autoejecuta en Container Apps como health probe
    """
    try:
        import sys
        import os
        from io import StringIO
        
        # Capturar output del checklist
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            # Importar y ejecutar el checklist simple para contexto web
            sys.path.append(os.path.dirname(__file__))
            
            # Usar el deployment_checklist completo que incluye RBAC
            try:
                from diagnostics.deployment_checklist import run_checklist
                from simple_checklist import load_env_file
                
                # Cargar variables de entorno
                load_env_file()
                
                # Ejecutar checklist completo incluyendo RBAC
                exit_code = run_checklist(['env', 'search', 'openai', 'rbac'])
                
                all_ok = (exit_code == 0)
            except Exception as e:
                print(f"❌ Error al ejecutar checklist completo: {e}")
                print("🔄 Fallback a checklist simple...")
                
                # Fallback al checklist simple
                from simple_checklist import (
                    load_env_file,
                    simple_check_azure_cli, 
                    simple_check_search, 
                    simple_check_openai
                )
                
                # Cargar variables de entorno
                load_env_file()
                
                print("🚀 Health Check (Fallback)")
                print("=" * 40)
                
                cli_ok = simple_check_azure_cli()
                search_ok = simple_check_search()
                openai_ok = simple_check_openai()
                
                print("\n📋 RESUMEN:")
                print(f"   ENV: {'✅' if cli_ok else '❌'}")
                print(f"   SEARCH: {'✅' if search_ok else '❌'}")
                print(f"   OPENAI: {'✅' if openai_ok else '❌'}")
                print(f"   RBAC: ⚠️ Error en validación: {str(e)}")
                
                all_ok = all([cli_ok, search_ok, openai_ok])
                exit_code = 1  # Forzar error debido a falla en RBAC
            
        finally:
            sys.stdout = old_stdout
        
        output = captured_output.getvalue()
        
        # Determinar estado
        if exit_code == 0:
            status = "healthy"
            http_status = 200
        else:
            status = "unhealthy" 
            http_status = 503  # Service Unavailable
        
        return jsonify({
            "status": status,
            "exit_code": exit_code,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "container-app" if os.getenv("RUNNING_IN_PRODUCTION") else "development",
            "detailed_output": output,
            "summary": {
                "environment_check": "✅" if "ENV: ✅" in output else "❌",
                "search_check": "✅" if "SEARCH: ✅" in output else "❌", 
                "openai_check": "✅" if "OPENAI: ✅" in output else "❌",
                "rbac_check": "✅" if "RBAC: ✅" in output else ("⚠️" if "RBAC: ⚠️" in output else "❌")
            }
        }), http_status
        
    except Exception as e:
        current_app.logger.error(f"Error en health_full_checklist: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@bp.route("/health", methods=["GET"])
async def health_simple():
    """Health check simple para Container Apps"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }), 200


@bp.before_app_serving
async def setup_clients():
    # Replace these with your own values, either in environment variables or directly here
    AZURE_STORAGE_ACCOUNT = os.environ["AZURE_STORAGE_ACCOUNT"]
    AZURE_STORAGE_CONTAINER = os.environ["AZURE_STORAGE_CONTAINER"]
    AZURE_USERSTORAGE_ACCOUNT = os.environ.get("AZURE_USERSTORAGE_ACCOUNT")
    AZURE_USERSTORAGE_CONTAINER = os.environ.get("AZURE_USERSTORAGE_CONTAINER")
    AZURE_SEARCH_SERVICE = os.environ["AZURE_SEARCH_SERVICE"]
    AZURE_SEARCH_ENDPOINT = f"https://{AZURE_SEARCH_SERVICE}.search.windows.net"
    AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
    AZURE_SEARCH_AGENT = os.getenv("AZURE_SEARCH_AGENT", "")
    # Shared by all OpenAI deployments
    OPENAI_HOST = os.getenv("OPENAI_HOST", "azure")
    OPENAI_CHATGPT_MODEL = os.environ["AZURE_OPENAI_CHATGPT_MODEL"]
    AZURE_OPENAI_SEARCHAGENT_MODEL = os.getenv("AZURE_OPENAI_SEARCHAGENT_MODEL")
    AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT = os.getenv("AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT")
    OPENAI_EMB_MODEL = os.getenv("AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002")
    OPENAI_EMB_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS") or 1536)
    OPENAI_REASONING_EFFORT = os.getenv("AZURE_OPENAI_REASONING_EFFORT")
    # Used with Azure OpenAI deployments
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_GPT4V_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT4V_DEPLOYMENT")
    AZURE_OPENAI_GPT4V_MODEL = os.environ.get("AZURE_OPENAI_GPT4V_MODEL")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") if OPENAI_HOST.startswith("azure") else None
    )
    AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT") if OPENAI_HOST.startswith("azure") else None
    AZURE_OPENAI_CUSTOM_URL = os.getenv("AZURE_OPENAI_CUSTOM_URL")
    # https://learn.microsoft.com/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION") or "2024-10-21"
    AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT", "")
    # Used only with non-Azure OpenAI deployments
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")

    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_USE_AUTHENTICATION = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    AZURE_ENFORCE_ACCESS_CONTROL = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS = os.getenv("AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS", "").lower() == "true"
    AZURE_ENABLE_UNAUTHENTICATED_ACCESS = os.getenv("AZURE_ENABLE_UNAUTHENTICATED_ACCESS", "").lower() == "true"
    AZURE_SERVER_APP_ID = os.getenv("AZURE_SERVER_APP_ID")
    AZURE_SERVER_APP_SECRET = os.getenv("AZURE_SERVER_APP_SECRET")
    AZURE_CLIENT_APP_ID = os.getenv("AZURE_CLIENT_APP_ID")
    AZURE_AUTH_TENANT_ID = os.getenv("AZURE_AUTH_TENANT_ID", AZURE_TENANT_ID)

    KB_FIELDS_CONTENT = os.getenv("KB_FIELDS_CONTENT", "content")
    KB_FIELDS_SOURCEPAGE = os.getenv("KB_FIELDS_SOURCEPAGE", "sourcepage")

    AZURE_SEARCH_QUERY_LANGUAGE = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE") or "en-us"
    AZURE_SEARCH_QUERY_SPELLER = os.getenv("AZURE_SEARCH_QUERY_SPELLER") or "lexicon"
    AZURE_SEARCH_SEMANTIC_RANKER = os.getenv("AZURE_SEARCH_SEMANTIC_RANKER", "free").lower()
    AZURE_SEARCH_QUERY_REWRITING = os.getenv("AZURE_SEARCH_QUERY_REWRITING", "false").lower()
    # This defaults to the previous field name "embedding", for backwards compatibility
    AZURE_SEARCH_FIELD_NAME_EMBEDDING = os.getenv("AZURE_SEARCH_FIELD_NAME_EMBEDDING", "embedding")

    AZURE_SPEECH_SERVICE_ID = os.getenv("AZURE_SPEECH_SERVICE_ID")
    AZURE_SPEECH_SERVICE_LOCATION = os.getenv("AZURE_SPEECH_SERVICE_LOCATION")
    AZURE_SPEECH_SERVICE_VOICE = os.getenv("AZURE_SPEECH_SERVICE_VOICE") or "en-US-AndrewMultilingualNeural"

    USE_GPT4V = os.getenv("USE_GPT4V", "").lower() == "true"
    USE_USER_UPLOAD = os.getenv("USE_USER_UPLOAD", "").lower() == "true"
    ENABLE_LANGUAGE_PICKER = os.getenv("ENABLE_LANGUAGE_PICKER", "").lower() == "true"
    USE_SPEECH_INPUT_BROWSER = os.getenv("USE_SPEECH_INPUT_BROWSER", "").lower() == "true"
    USE_SPEECH_OUTPUT_BROWSER = os.getenv("USE_SPEECH_OUTPUT_BROWSER", "").lower() == "true"
    USE_SPEECH_OUTPUT_AZURE = os.getenv("USE_SPEECH_OUTPUT_AZURE", "").lower() == "true"
    USE_CHAT_HISTORY_BROWSER = os.getenv("USE_CHAT_HISTORY_BROWSER", "").lower() == "true"
    USE_CHAT_HISTORY_COSMOS = os.getenv("USE_CHAT_HISTORY_COSMOS", "").lower() == "true"
    USE_AGENTIC_RETRIEVAL = os.getenv("USE_AGENTIC_RETRIEVAL", "").lower() == "true"
    SHAREPOINT_BASE_URL = os.getenv("SHAREPOINT_BASE_URL", "https://lumston.sharepoint.com/sites/AIBotProjectAutomation")

    # WEBSITE_HOSTNAME is always set by App Service, RUNNING_IN_PRODUCTION is set in main.bicep
    RUNNING_ON_AZURE = os.getenv("WEBSITE_HOSTNAME") is not None or os.getenv("RUNNING_IN_PRODUCTION") is not None

    # Use our custom credential provider for robust authentication
    # This automatically selects ClientSecretCredential for local dev or ManagedIdentity for Azure
    from core.azure_credential import get_azure_credential_async, validate_azure_credentials
    
    # Validar configuración para debugging
    current_app.logger.info("🔍 Iniciando validación de credenciales de Azure...")
    validate_azure_credentials()
    
    # Obtener la credencial correcta para el entorno
    try:
        azure_credential = get_azure_credential_async()
        current_app.logger.info(f"✅ Credencial configurada: {type(azure_credential).__name__}")
    except Exception as e:
        current_app.logger.error(f"💥 Error configurando credencial de Azure: {str(e)}")
        raise

    # Set the Azure credential in the app config for use in other parts of the app
    current_app.config[CONFIG_CREDENTIAL] = azure_credential

    # Set up clients for AI Search and Storage
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=azure_credential,
    )
    
    # Validación opcional de Azure Search si está habilitada
    if os.getenv("AZURE_VALIDATE_SEARCH", "").lower() == "true":
        current_app.logger.info("🔍 AZURE_VALIDATE_SEARCH=true, ejecutando validaciones de Azure Search...")
        try:
            from healthchecks.search import (
                validate_search_environment_vars, 
                validate_search_credential_scope, 
                validate_search_access
            )
            
            # Validar variables de entorno
            env_check = validate_search_environment_vars()
            if env_check["status"] == "error":
                current_app.logger.error("❌ Error en variables de entorno de Azure Search")
                raise ValueError(f"Variables de entorno faltantes: {env_check['missing_required']}")
            
            # Validar scope de credencial
            scope_valid = await validate_search_credential_scope(azure_credential)
            if not scope_valid:
                current_app.logger.error("❌ Credencial no puede obtener tokens para Azure Search")
                raise ValueError("Credencial inválida para Azure Search")
            
            # Validar acceso completo
            access_valid = await validate_search_access(AZURE_SEARCH_ENDPOINT, azure_credential, AZURE_SEARCH_INDEX)
            if not access_valid:
                current_app.logger.error("❌ No se pudo validar acceso a Azure Search")
                raise ValueError("Acceso a Azure Search falló")
                
            current_app.logger.info("✅ Validaciones de Azure Search completadas exitosamente")
            
        except Exception as e:
            current_app.logger.error(f"💥 Error crítico en validación de Azure Search: {str(e)}")
            if os.getenv("AZURE_STRICT_VALIDATION", "").lower() == "true":
                raise  # Fallar completamente si strict mode está habilitado
            else:
                current_app.logger.warning("⚠️ Continuando a pesar del error de validación (AZURE_STRICT_VALIDATION no está habilitado)")
    
    agent_client = KnowledgeAgentRetrievalClient(
        endpoint=AZURE_SEARCH_ENDPOINT, agent_name=AZURE_SEARCH_AGENT, credential=azure_credential
    )

    blob_container_client = ContainerClient(
        f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", AZURE_STORAGE_CONTAINER, credential=azure_credential
    )

    # Set up authentication helper
    search_index = None
    if AZURE_USE_AUTHENTICATION:
        current_app.logger.info("AZURE_USE_AUTHENTICATION is true, setting up search index client")
        search_index_client = SearchIndexClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            credential=azure_credential,
        )
        search_index = await search_index_client.get_index(AZURE_SEARCH_INDEX)
        await search_index_client.close()
    auth_helper = AuthenticationHelper(
        search_index=search_index,
        use_authentication=AZURE_USE_AUTHENTICATION,
        server_app_id=AZURE_SERVER_APP_ID,
        server_app_secret=AZURE_SERVER_APP_SECRET,
        client_app_id=AZURE_CLIENT_APP_ID,
        tenant_id=AZURE_AUTH_TENANT_ID,
        require_access_control=AZURE_ENFORCE_ACCESS_CONTROL,
        enable_global_documents=AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS,
        enable_unauthenticated_access=AZURE_ENABLE_UNAUTHENTICATED_ACCESS,
    )

    if USE_USER_UPLOAD:
        current_app.logger.info("USE_USER_UPLOAD is true, setting up user upload feature")
        if not AZURE_USERSTORAGE_ACCOUNT or not AZURE_USERSTORAGE_CONTAINER:
            raise ValueError(
                "AZURE_USERSTORAGE_ACCOUNT and AZURE_USERSTORAGE_CONTAINER must be set when USE_USER_UPLOAD is true"
            )
        user_blob_container_client = FileSystemClient(
            f"https://{AZURE_USERSTORAGE_ACCOUNT}.dfs.core.windows.net",
            AZURE_USERSTORAGE_CONTAINER,
            credential=azure_credential,
        )
        current_app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT] = user_blob_container_client

        # Set up ingester
        file_processors = setup_file_processors(
            azure_credential=azure_credential,
            document_intelligence_service=os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE"),
            local_pdf_parser=os.getenv("USE_LOCAL_PDF_PARSER", "").lower() == "true",
            local_html_parser=os.getenv("USE_LOCAL_HTML_PARSER", "").lower() == "true",
            search_images=USE_GPT4V,
        )
        search_info = await setup_search_info(
            search_service=AZURE_SEARCH_SERVICE, index_name=AZURE_SEARCH_INDEX, azure_credential=azure_credential
        )
        text_embeddings_service = setup_embeddings_service(
            azure_credential=azure_credential,
            openai_host=OPENAI_HOST,
            openai_model_name=OPENAI_EMB_MODEL,
            openai_service=AZURE_OPENAI_SERVICE,
            openai_custom_url=AZURE_OPENAI_CUSTOM_URL,
            openai_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
            openai_dimensions=OPENAI_EMB_DIMENSIONS,
            openai_api_version=AZURE_OPENAI_API_VERSION,
            openai_key=clean_key_if_exists(OPENAI_API_KEY),
            openai_org=OPENAI_ORGANIZATION,
            disable_vectors=os.getenv("USE_VECTORS", "").lower() == "false",
        )
        ingester = UploadUserFileStrategy(
            search_info=search_info,
            embeddings=text_embeddings_service,
            file_processors=file_processors,
            search_field_name_embedding=AZURE_SEARCH_FIELD_NAME_EMBEDDING,
        )
        current_app.config[CONFIG_INGESTER] = ingester

    # Used by the OpenAI SDK
    openai_client: AsyncOpenAI

    if USE_SPEECH_OUTPUT_AZURE:
        current_app.logger.info("USE_SPEECH_OUTPUT_AZURE is true, setting up Azure speech service")
        if not AZURE_SPEECH_SERVICE_ID or AZURE_SPEECH_SERVICE_ID == "":
            raise ValueError("Azure speech resource not configured correctly, missing AZURE_SPEECH_SERVICE_ID")
        if not AZURE_SPEECH_SERVICE_LOCATION or AZURE_SPEECH_SERVICE_LOCATION == "":
            raise ValueError("Azure speech resource not configured correctly, missing AZURE_SPEECH_SERVICE_LOCATION")
        current_app.config[CONFIG_SPEECH_SERVICE_ID] = AZURE_SPEECH_SERVICE_ID
        current_app.config[CONFIG_SPEECH_SERVICE_LOCATION] = AZURE_SPEECH_SERVICE_LOCATION
        current_app.config[CONFIG_SPEECH_SERVICE_VOICE] = AZURE_SPEECH_SERVICE_VOICE
        # Wait until token is needed to fetch for the first time
        current_app.config[CONFIG_SPEECH_SERVICE_TOKEN] = None

    if OPENAI_HOST.startswith("azure"):
        if OPENAI_HOST == "azure_custom":
            current_app.logger.info("OPENAI_HOST is azure_custom, setting up Azure OpenAI custom client")
            if not AZURE_OPENAI_CUSTOM_URL:
                raise ValueError("AZURE_OPENAI_CUSTOM_URL must be set when OPENAI_HOST is azure_custom")
            endpoint = AZURE_OPENAI_CUSTOM_URL
        else:
            current_app.logger.info("OPENAI_HOST is azure, setting up Azure OpenAI client")
            if not AZURE_OPENAI_SERVICE:
                raise ValueError("AZURE_OPENAI_SERVICE must be set when OPENAI_HOST is azure")
            endpoint = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
        if api_key := os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"):
            current_app.logger.info("AZURE_OPENAI_API_KEY_OVERRIDE found, using as api_key for Azure OpenAI client")
            openai_client = AsyncAzureOpenAI(
                api_version=AZURE_OPENAI_API_VERSION, azure_endpoint=endpoint, api_key=api_key
            )
        else:
            current_app.logger.info("Using Azure credential (passwordless authentication) for Azure OpenAI client")
            token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
            openai_client = AsyncAzureOpenAI(
                api_version=AZURE_OPENAI_API_VERSION,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
            )
    elif OPENAI_HOST == "local":
        current_app.logger.info("OPENAI_HOST is local, setting up local OpenAI client for OPENAI_BASE_URL with no key")
        openai_client = AsyncOpenAI(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key="no-key-required",
        )
    else:
        current_app.logger.info(
            "OPENAI_HOST is not azure, setting up OpenAI client using OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables"
        )
        openai_client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            organization=OPENAI_ORGANIZATION,
        )

    current_app.config[CONFIG_OPENAI_CLIENT] = openai_client
    current_app.config[CONFIG_SEARCH_CLIENT] = search_client
    current_app.config[CONFIG_AGENT_CLIENT] = agent_client
    current_app.config[CONFIG_BLOB_CONTAINER_CLIENT] = blob_container_client
    current_app.config[CONFIG_AUTH_CLIENT] = auth_helper

    current_app.config[CONFIG_GPT4V_DEPLOYED] = bool(USE_GPT4V)
    current_app.config[CONFIG_SEMANTIC_RANKER_DEPLOYED] = AZURE_SEARCH_SEMANTIC_RANKER != "disabled"
    current_app.config[CONFIG_QUERY_REWRITING_ENABLED] = (
        AZURE_SEARCH_QUERY_REWRITING == "true" and AZURE_SEARCH_SEMANTIC_RANKER != "disabled"
    )
    current_app.config[CONFIG_DEFAULT_REASONING_EFFORT] = OPENAI_REASONING_EFFORT
    current_app.config[CONFIG_REASONING_EFFORT_ENABLED] = OPENAI_CHATGPT_MODEL in Approach.GPT_REASONING_MODELS
    current_app.config[CONFIG_STREAMING_ENABLED] = (
        bool(USE_GPT4V)
        or OPENAI_CHATGPT_MODEL not in Approach.GPT_REASONING_MODELS
        or Approach.GPT_REASONING_MODELS[OPENAI_CHATGPT_MODEL].streaming
    )
    current_app.config[CONFIG_VECTOR_SEARCH_ENABLED] = os.getenv("USE_VECTORS", "").lower() != "false"
    current_app.config[CONFIG_USER_UPLOAD_ENABLED] = bool(USE_USER_UPLOAD)
    current_app.config[CONFIG_LANGUAGE_PICKER_ENABLED] = ENABLE_LANGUAGE_PICKER
    current_app.config[CONFIG_SPEECH_INPUT_ENABLED] = USE_SPEECH_INPUT_BROWSER
    current_app.config[CONFIG_SPEECH_OUTPUT_BROWSER_ENABLED] = USE_SPEECH_OUTPUT_BROWSER
    current_app.config[CONFIG_SPEECH_OUTPUT_AZURE_ENABLED] = USE_SPEECH_OUTPUT_AZURE
    current_app.config[CONFIG_CHAT_HISTORY_BROWSER_ENABLED] = USE_CHAT_HISTORY_BROWSER
    current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED] = USE_CHAT_HISTORY_COSMOS
    current_app.config[CONFIG_AGENTIC_RETRIEVAL_ENABLED] = USE_AGENTIC_RETRIEVAL
    current_app.config[CONFIG_SHAREPOINT_BASE_URL] = SHAREPOINT_BASE_URL

    prompt_manager = PromptyManager()

    # Set up the two default RAG approaches for /ask and /chat
    # RetrieveThenReadApproach is used by /ask for single-turn Q&A
    current_app.config[CONFIG_ASK_APPROACH] = RetrieveThenReadApproach(
        search_client=search_client,
        search_index_name=AZURE_SEARCH_INDEX,
        agent_model=AZURE_OPENAI_SEARCHAGENT_MODEL,
        agent_deployment=AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT,
        agent_client=agent_client,
        openai_client=openai_client,
        auth_helper=auth_helper,
        chatgpt_model=OPENAI_CHATGPT_MODEL,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=OPENAI_EMB_MODEL,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        embedding_dimensions=OPENAI_EMB_DIMENSIONS,
        embedding_field=AZURE_SEARCH_FIELD_NAME_EMBEDDING,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
        prompt_manager=prompt_manager,
        reasoning_effort=OPENAI_REASONING_EFFORT,
    )

    # ChatReadRetrieveReadApproach is used by /chat for multi-turn conversation
    current_app.config[CONFIG_CHAT_APPROACH] = ChatReadRetrieveReadApproach(
        search_client=search_client,
        search_index_name=AZURE_SEARCH_INDEX,
        agent_model=AZURE_OPENAI_SEARCHAGENT_MODEL,
        agent_deployment=AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT,
        agent_client=agent_client,
        openai_client=openai_client,
        auth_helper=auth_helper,
        chatgpt_model=OPENAI_CHATGPT_MODEL,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=OPENAI_EMB_MODEL,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        embedding_dimensions=OPENAI_EMB_DIMENSIONS,
        embedding_field=AZURE_SEARCH_FIELD_NAME_EMBEDDING,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
        prompt_manager=prompt_manager,
        reasoning_effort=OPENAI_REASONING_EFFORT,
    )

    if USE_GPT4V:
        current_app.logger.info("USE_GPT4V is true, setting up GPT4V approach")
        if not AZURE_OPENAI_GPT4V_MODEL:
            raise ValueError("AZURE_OPENAI_GPT4V_MODEL must be set when USE_GPT4V is true")
        if any(
            model in Approach.GPT_REASONING_MODELS
            for model in [
                OPENAI_CHATGPT_MODEL,
                AZURE_OPENAI_GPT4V_MODEL,
                AZURE_OPENAI_CHATGPT_DEPLOYMENT,
                AZURE_OPENAI_GPT4V_DEPLOYMENT,
            ]
        ):
            raise ValueError(
                "AZURE_OPENAI_CHATGPT_MODEL and AZURE_OPENAI_GPT4V_MODEL must not be a reasoning model when USE_GPT4V is true"
            )

        token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")

        current_app.config[CONFIG_ASK_VISION_APPROACH] = RetrieveThenReadVisionApproach(
            search_client=search_client,
            openai_client=openai_client,
            blob_container_client=blob_container_client,
            auth_helper=auth_helper,
            vision_endpoint=AZURE_VISION_ENDPOINT,
            vision_token_provider=token_provider,
            gpt4v_deployment=AZURE_OPENAI_GPT4V_DEPLOYMENT,
            gpt4v_model=AZURE_OPENAI_GPT4V_MODEL,
            embedding_model=OPENAI_EMB_MODEL,
            embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
            embedding_dimensions=OPENAI_EMB_DIMENSIONS,
            embedding_field=AZURE_SEARCH_FIELD_NAME_EMBEDDING,
            sourcepage_field=KB_FIELDS_SOURCEPAGE,
            content_field=KB_FIELDS_CONTENT,
            query_language=AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=AZURE_SEARCH_QUERY_SPELLER,
            prompt_manager=prompt_manager,
        )

        current_app.config[CONFIG_CHAT_VISION_APPROACH] = ChatReadRetrieveReadVisionApproach(
            search_client=search_client,
            openai_client=openai_client,
            blob_container_client=blob_container_client,
            auth_helper=auth_helper,
            vision_endpoint=AZURE_VISION_ENDPOINT,
            vision_token_provider=token_provider,
            chatgpt_model=OPENAI_CHATGPT_MODEL,
            chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            gpt4v_deployment=AZURE_OPENAI_GPT4V_DEPLOYMENT,
            gpt4v_model=AZURE_OPENAI_GPT4V_MODEL,
            embedding_model=OPENAI_EMB_MODEL,
            embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
            embedding_dimensions=OPENAI_EMB_DIMENSIONS,
            embedding_field=AZURE_SEARCH_FIELD_NAME_EMBEDDING,
            sourcepage_field=KB_FIELDS_SOURCEPAGE,
            content_field=KB_FIELDS_CONTENT,
            query_language=AZURE_SEARCH_QUERY_LANGUAGE,
            query_speller=AZURE_SEARCH_QUERY_SPELLER,
            prompt_manager=prompt_manager,
        )


@bp.after_app_serving
async def close_clients():
    await current_app.config[CONFIG_SEARCH_CLIENT].close()
    await current_app.config[CONFIG_BLOB_CONTAINER_CLIENT].close()
    if current_app.config.get(CONFIG_USER_BLOB_CONTAINER_CLIENT):
        await current_app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT].close()


def create_app():
    app = Quart(__name__)
    app.register_blueprint(bp)
    app.register_blueprint(chat_history_cosmosdb_bp)

    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        app.logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING is set, enabling Azure Monitor")
        configure_azure_monitor()
        # This tracks HTTP requests made by aiohttp:
        AioHttpClientInstrumentor().instrument()
        # This tracks HTTP requests made by httpx:
        HTTPXClientInstrumentor().instrument()
        # This tracks OpenAI SDK requests:
        OpenAIInstrumentor().instrument()
        # This middleware tracks app route requests:
        app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)  # type: ignore[assignment]

    # Log levels should be one of https://docs.python.org/3/library/logging.html#logging-levels
    # Set root level to WARNING to avoid seeing overly verbose logs from SDKS
    logging.basicConfig(level=logging.WARNING)
    # Set our own logger levels to INFO by default
    app_level = os.getenv("APP_LOG_LEVEL", "INFO")
    app.logger.setLevel(os.getenv("APP_LOG_LEVEL", app_level))
    logging.getLogger("scripts").setLevel(app_level)

    if allowed_origin := os.getenv("ALLOWED_ORIGIN"):
        allowed_origins = allowed_origin.split(";")
        if len(allowed_origins) > 0:
            app.logger.info("CORS enabled for %s", allowed_origins)
            cors(app, allow_origin=allowed_origins, allow_methods=["GET", "POST"])

    return app

if __name__ == "__main__":
    # Validar entorno antes de iniciar el bot
    try:
        init_bot_context()
        print("🎯 Iniciando validación de runtime...")
        # validate_runtime_status() se ejecutará después de que la app esté corriendo
    except Exception as e:
        print(f"🛑 Error crítico en inicialización: {e}")
        exit(1)
    
    app = create_app()
    app.run(debug=True)
