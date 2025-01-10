import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

import os
import time
from typing import Any, Dict, Union

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.identity.aio import AzureDeveloperCliCredential, ManagedIdentityCredential
from quart import Blueprint, current_app, jsonify, request

from config import (
CONFIG_CHAT_HISTORY_MONGO_ENABLED,
CONFIG_MONGO_HISTORY_CONTAINER,
CONFIG_MONGO_HISTORY_CLIENT
)
from decorators import authenticated
from error import error_response

chat_history_mongodb_bp = Blueprint("chat_history_mongo", __name__, static_folder="static")


@chat_history_mongodb_bp.post("/chat_history")
@authenticated
async def post_chat_history(auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_MONGO_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: pymongo.collection.Collection = current_app.config[CONFIG_MONGO_HISTORY_CONTAINER]
    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        request_json = await request.get_json()
        id = request_json.get("id")
        answers = request_json.get("answers")
        title = answers[0][0][:50] + "..." if len(answers[0][0]) > 50 else answers[0][0]
        timestamp = int(time.time() * 1000)

        container.update_one(
            {"id": id},
            {"$set": {"entra_oid": entra_oid, "title": title, "answers": answers, "timestamp": timestamp}},
            upsert=True
            )

        return jsonify({}), 201
    except Exception as error:
        return error_response(error, "/chat_history")


@chat_history_mongodb_bp.post("/chat_history/items")
@authenticated
async def get_chat_history(auth_claims: Dict[str, Any]):
    if not current_app.config[CONFIG_CHAT_HISTORY_MONGO_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: pymongo.collection.Collection = current_app.config[CONFIG_MONGO_HISTORY_CONTAINER]

    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        request_json = await request.get_json()
        count = request_json.get("count", 20)
        continuation_token = request_json.get("continuation_token")

        items = []

        result = container.find({"entra_oid": entra_oid}).sort("timestamp", -1).limit(count)

        for item in result:
            items.append(
                {
                    "id": item.get("id"),
                    "entra_oid": item.get("entra_oid"),
                    "title": item.get("title", "untitled"),
                    "timestamp": item.get("timestamp"),
                }
            )

        return jsonify({"items": items, "continuation_token": continuation_token}), 200

    except Exception as error:
        return error_response(error, "/chat_history/items")


@chat_history_mongodb_bp.get("/chat_history/items/<item_id>")
@authenticated
async def get_chat_history_session(auth_claims: Dict[str, Any], item_id: str):
    if not current_app.config[CONFIG_CHAT_HISTORY_MONGO_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: pymongo.collection.Collection = current_app.config[CONFIG_MONGO_HISTORY_CONTAINER]

    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:

        result = container.find_one({"id": item_id})

        return (
            jsonify(
                {
                    "id": result.get("id"),
                    "entra_oid": result.get("entra_oid"),
                    "title": result.get("title", "untitled"),
                    "timestamp": result.get("timestamp"),
                    "answers": result.get("answers", []),
                }
            ),
            200,
        )
    except Exception as error:
        return error_response(error, f"/chat_history/items/{item_id}")


@chat_history_mongodb_bp.delete("/chat_history/items/<item_id>")
@authenticated
async def delete_chat_history_session(auth_claims: Dict[str, Any], item_id: str):
    if not current_app.config[CONFIG_CHAT_HISTORY_MONGO_ENABLED]:
        return jsonify({"error": "Chat history not enabled"}), 400

    container: pymongo.collection.Collection = current_app.config[CONFIG_MONGO_HISTORY_CONTAINER]

    if not container:
        return jsonify({"error": "Chat history not enabled"}), 400

    entra_oid = auth_claims.get("oid")
    if not entra_oid:
        return jsonify({"error": "User OID not found"}), 401

    try:
        container.delete_one({"id": item_id})
        return jsonify({}), 204
    except Exception as error:
        return error_response(error, f"/chat_history/items/{item_id}")


@chat_history_mongodb_bp.before_app_serving
async def setup_clients():
    USE_CHAT_HISTORY_MONGODB = os.getenv("USE_CHAT_HISTORY_MONGO", "").lower() == "true"
    MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")
    MONGODB_COLLECTION_NAME= os.getenv("MONGODB_COLLECTION_NAME")

    if USE_CHAT_HISTORY_MONGODB:
        current_app.logger.info("USE_CHAT_HISTORY_MONGODB is true, setting up MongoDB client")
        if not MONGODB_CONNECTION_STRING:
            raise ValueError("MONGODB_CONNECTION_STRING must be set when USE_CHAT_HISTORY_MONGODB is true")
        if not MONGODB_DB_NAME:
            raise ValueError("MONGODB_DB_NAME must be set when USE_CHAT_HISTORY_MONGODB is true")
        if not MONGODB_COLLECTION_NAME:
            raise ValueError("MONGODB_COLLECTION_NAME must be set when USE_CHAT_HISTORY_MONGODB is true")

        mongodb_client = MongoClient(MONGODB_CONNECTION_STRING)
        mongodb_db = mongodb_client[MONGODB_DB_NAME]
        mongodb_collection = mongodb_db[MONGODB_COLLECTION_NAME]

        current_app.config[CONFIG_MONGO_HISTORY_CLIENT] = mongodb_client
        current_app.config[CONFIG_MONGO_HISTORY_CONTAINER] = mongodb_collection


@chat_history_mongodb_bp.after_app_serving
async def close_clients():
    if current_app.config.get(CONFIG_MONGO_HISTORY_CLIENT):
        mongodb_client: MongoClient = current_app.config[CONFIG_MONGO_HISTORY_CLIENT]
        mongodb_client.close()
