import logging
import os
import time
from typing import Any, Dict, Union

from azure.cosmos import exceptions
from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.identity.aio import AzureDeveloperCliCredential, ManagedIdentityCredential
from quart import Blueprint, current_app, jsonify, request

from config import (
    CONFIG_CHAT_HISTORY_COSMOS_ENABLED,
    CONFIG_COSMOS_HISTORY_CLIENT,
    CONFIG_COSMOS_HISTORY_CONTAINER,
    CONFIG_CREDENTIAL,
)
from decorators import authenticated
from error import error_response

logger = logging.getLogger("scripts")

chat_history_cosmosdb_bp = Blueprint("chat_history_cosmos", __name__, static_folder="static")


def make_partition_key(entra_id, session_id=None):
    if entra_id and session_id:
        # Need multihash for hierachical partitioning
        return PartitionKey(path=["/entra_id", "/session_id"], kind="MultiHash")
    else:
        return PartitionKey(path="/entra_id")


@chat_history_cosmosdb_bp.post("/chat_history")
@authenticated
async def post_chat_history(auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: ContainerProxy = current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER]
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        request_json = await request.get_json()
        session_id = request_json.get("id")
        answers = request_json.get("answers")
        title = answers[0][0][:50] + "..." if len(answers[0][0]) > 50 else answers[0][0]
        timestamp = int(time.time() * 1000)

        # Insert the session item:
        session_item = {
            "id": id,
            "session_id": session_id,
            "entra_oid": entra_oid,
            "type": "session",
            "title": title,
            "timestamp": timestamp,
        }

        message_items = []
        # Now insert a message item for each question/response pair:
        for ind, message_pair in enumerate(zip(answers[::2], answers[1::2])):
            # The id: what if you delete a message and then add a new one? The id will be the same.
            # If we had delete mechanism, and you deleted item 5 in a history, then item 6 would still hang around
            # and youd have two of item 6.
            # abc-0
            # abc-1
            # abc-2 <-- DELETE
            # abc-3
            # One approach would be to delete EVERYTHING, then upsert everything.
            # Another approach would be to delete item plus everything after, then upsert everything after.
            # Or: Change the frontend?
            # We can do this first, and change the frontend after
            message_items.append(
                {
                    "id": f"{session_id}-{ind}",
                    "session_id": id,
                    "entra_oid": entra_oid,
                    "type": "message",
                    "question": message_pair[0],
                    "response": message_pair[1],
                    "timestamp": timestamp,  # <-- This is the timestamp of the session, not the message
                }
            )

        batch_operations = [("upsert", tuple([session_item] + message_items), {})]

        try:
            # Run that list of operations
            batch_results = container.execute_item_batch(
                batch_operations=batch_operations, partition_key=make_partition_key(entra_oid, session_id)
            )
            # Batch results are returned as a list of item operation results - or raise a CosmosBatchOperationError if
            # one of the operations failed within your batch request.
            print(f"\nResults for the batch operations: {batch_results}\n")
        except exceptions.CosmosBatchOperationError as e:
            error_operation_index = e.error_index
            error_operation_response = e.operation_responses[error_operation_index]
            error_operation = batch_operations[error_operation_index]
            logger.error(f"Batch operation failed: {error_operation_response} for operation {error_operation}")
            return jsonify({"error": "Batch operation failed"}), 400
        return jsonify({}), 201
    except Exception as error:
        return error_response(error, "/chat_history")


@chat_history_cosmosdb_bp.get("/chat_history/items")
@authenticated
async def get_chat_history(auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: ContainerProxy = current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER]
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        # get the count and continuation token from the request URL
        count = request.args.get("count", 10)
        continuation_token = request.args.get("continuation_token")

        res = container.query_items(
            # TODO: do we need distinct? per Mark's code - Mark says no!
            query="SELECT c.id, c.entra_oid, c.title, c.timestamp FROM c WHERE c.entra_oid = @entra_oid AND c.type = @type ORDER BY c.timestamp DESC",
            parameters=[dict(name="@entra_oid", value=entra_oid), dict(name="@type", value="session")],
            partition_key=make_partition_key(entra_oid),
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
                items.append(
                    {
                        "id": item.get("id"),
                        "entra_oid": item.get("entra_oid"),
                        "title": item.get("title", "untitled"),
                        "timestamp": item.get("timestamp"),
                    }
                )

        # If there are no more pages, StopAsyncIteration is raised
        except StopAsyncIteration:
            items = []
            continuation_token = None

        return jsonify({"items": items, "continuation_token": continuation_token}), 200

    except Exception as error:
        return error_response(error, "/chat_history/items")


@chat_history_cosmosdb_bp.get("/chat_history/items/<item_id>")
@authenticated
async def get_chat_history_session(auth_claims: Dict[str, Any], item_id: str):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: ContainerProxy = current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER]
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        res = container.query_items(
            # TODO: do we need distinct? per Mark's code
            query="SELECT c.id, c.entra_oid, c.title, c.timestamp FROM c WHERE c.session_id = @session_id ORDER BY c.timestamp DESC",
            parameters=[dict(name="@entra_oid", value=entra_oid), dict(name="@session_id", value=item_id)],
            partition_key=make_partition_key(entra_oid, item_id),
            # max_item_count=?
        )

        res = await container.read_item(item=item_id, partition_key=entra_oid)
        return (
            jsonify(
                {
                    "id": res.get("id"),
                    "entra_oid": res.get("entra_oid"),
                    "title": res.get("title", "untitled"),
                    "timestamp": res.get("timestamp"),
                    "answers": res.get("answers", []),
                }
            ),
            200,
        )
    except Exception as error:
        return error_response(error, f"/chat_history/items/{item_id}")


@chat_history_cosmosdb_bp.delete("/chat_history/items/<item_id>")
@authenticated
async def delete_chat_history_session(auth_claims: Dict[str, Any], item_id: str):
    if not current_app.config[CONFIG_CHAT_HISTORY_COSMOS_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: ContainerProxy = current_app.config[CONFIG_COSMOS_HISTORY_CONTAINER]
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        await container.delete_item(item=item_id, partition_key=entra_oid)
        # Delete session, and all the message items associated with it
        # TODO: Delete all the message items as well
        return jsonify({}), 204
    except Exception as error:
        return error_response(error, f"/chat_history/items/{item_id}")


@chat_history_cosmosdb_bp.before_app_serving
async def setup_clients():
    USE_CHAT_HISTORY_COSMOS = os.getenv("USE_CHAT_HISTORY_COSMOS", "").lower() == "true"
    AZURE_COSMOSDB_ACCOUNT = os.getenv("AZURE_COSMOSDB_ACCOUNT")
    AZURE_CHAT_HISTORY_DATABASE = os.getenv("AZURE_CHAT_HISTORY_DATABASE")
    AZURE_CHAT_HISTORY_CONTAINER = os.getenv("AZURE_CHAT_HISTORY_CONTAINER")

    azure_credential: Union[AzureDeveloperCliCredential, ManagedIdentityCredential] = current_app.config[
        CONFIG_CREDENTIAL
    ]

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
    if current_app.config.get(CONFIG_COSMOS_HISTORY_CLIENT):
        cosmos_client: CosmosClient = current_app.config[CONFIG_COSMOS_HISTORY_CLIENT]
        await cosmos_client.close()
