import os
from typing import Any, Dict, Union, cast

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.identity.aio import AzureDeveloperCliCredential, ManagedIdentityCredential
from quart import Blueprint, current_app, jsonify, request

from config import (
    CONFIG_CHAT_HISTORY_COSMOS_ENABLED,
    CONFIG_COSMOS_HISTORY_CLIENT,
    CONFIG_COSMOS_HISTORY_CONTAINER,
    CONFIG_CREDENTIAL,
)
from decorators import authenticated, authenticated_path
from error import error_response

chat_history_cosmosdb_bp = Blueprint("chat_history_cosmos", __name__, static_folder="static")


@chat_history_cosmosdb_bp.post("/chat_history")
@authenticated
async def post_chat_history(auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 405

    container = cast(ContainerProxy, current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER])
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 405

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        request_json = await request.get_json()
        id = request_json.get("id")
        answers = request_json.get("answers")
        title = answers[0][0][:50] + "..." if len(answers[0][0]) > 50 else answers[0][0]

        await container.upsert_item({"id": id, "entra_oid": entra_oid, "title": title, "answers": answers})

        return jsonify({}), 201
    except Exception as error:
        return error_response(error, "/chat_history")


@chat_history_cosmosdb_bp.post("/chat_history/items")
@authenticated
async def get_chat_history(auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 405

    container = cast(ContainerProxy, current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER])
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 405

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        request_json = await request.get_json()
        count = request_json.get("count", 20)
        continuation_token = request_json.get("continuation_token")

        res = container.query_items(
            query="SELECT c.id, c.entra_oid, c.title, c._ts FROM c WHERE c.entra_oid = @entra_oid ORDER BY c._ts DESC",
            parameters=[dict(name="@entra_oid", value=entra_oid)],
            max_item_count=count,
        )

        # set the continuation token for the next page
        pager = res.by_page(continuation_token)

        # Get the first page, and the continuation token
        try:
            page = await pager.__anext__()
            continuation_token = pager.continuation_token  # type: ignore

            items = []
            async for item in page:
                items.append(item)

        # If there are no page, StopAsyncIteration is raised
        except StopAsyncIteration:
            items = []
            continuation_token = None

        return jsonify({"items": items, "continuation_token": continuation_token}), 200

    except Exception as error:
        return error_response(error, "/chat_history/items")


@chat_history_cosmosdb_bp.get("/chat_history/items/<path>")
@authenticated_path
async def get_chat_history_session(path: str, auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 405

    container = cast(ContainerProxy, current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER])
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 405

    if not path:
        return jsonify({"error": "Invalid path"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        res = await container.read_item(item=path, partition_key=entra_oid)
        return jsonify(res), 200
    except Exception as error:
        return error_response(error, f"/chat_history/items/{path}")


@chat_history_cosmosdb_bp.delete("/chat_history/items/<path>")
@authenticated_path
async def delete_chat_history_session(path: str, auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 405

    container = cast(ContainerProxy, current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER])
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 405

    if not path:
        return jsonify({"error": "Invalid path"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        await container.delete_item(item=path, partition_key=entra_oid)
        return jsonify({}), 200
    except Exception as error:
        return error_response(error, f"/chat_history/items/{path}")


@chat_history_cosmosdb_bp.before_app_serving
async def setup_clients():
    USE_CHAT_HISTORY_COSMOS = os.getenv("USE_CHAT_HISTORY_COSMOS", "").lower() == "true"
    AZURE_COSMOSDB_ACCOUNT = os.getenv("AZURE_COSMOSDB_ACCOUNT")
    AZURE_CHAT_HISTORY_DATABASE = os.getenv("AZURE_CHAT_HISTORY_DATABASE")
    AZURE_CHAT_HISTORY_CONTAINER = os.getenv("AZURE_CHAT_HISTORY_CONTAINER")

    azure_credential = cast(
        Union[AzureDeveloperCliCredential, ManagedIdentityCredential], current_app.config[CONFIG_CREDENTIAL]
    )

    if USE_CHAT_HISTORY_COSMOS:
        current_app.logger.info("USE_CHAT_HISTORY_COSMOS is true, setting up CosmosDB client")
        if not AZURE_COSMOSDB_ACCOUNT:
            raise ValueError("AZURE_COSMOSDB_ACCOUNT must be set when USE_CHAT_HISTORY_COSMOS is true")
        if not AZURE_CHAT_HISTORY_DATABASE:
            raise ValueError("AZURE_CHAT_HISTORY_DATABASE must be set when USE_CHAT_HISTORY_COSMOS is true")
        if not AZURE_CHAT_HISTORY_CONTAINER:
            raise ValueError("AZURE_CHAT_HISTORY_CONTAINER must be set when USE_CHAT_HISTORY_COSMOS is true")
        cosmos_client = CosmosClient(
            url=f"https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/", credential=azure_credential
        )
        cosmos_db = cosmos_client.get_database_client(AZURE_CHAT_HISTORY_DATABASE)
        cosmos_container = cosmos_db.get_container_client(AZURE_CHAT_HISTORY_CONTAINER)

        current_app.config[CONFIG_COSMOS_HISTORY_CLIENT] = cosmos_client
        current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER] = cosmos_container


@chat_history_cosmosdb_bp.after_app_serving
async def close_clients():
    cosmos_client = cast(CosmosClient, current_app.config.get(CONFIG_COSMOS_HISTORY_CLIENT))
    if cosmos_client:
        await cosmos_client.close()
