import os
import datetime
import uuid
from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential  
from azure.cosmos import CosmosClient, PartitionKey  
  
class CosmosDbService():
    
    def __init__(self, cosmosdb_endpoint: str, cosmosdb_conversations_container: str, cosmosdb_messages_container: str):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.cosmosdb_conversations_container = cosmosdb_conversations_container
        self.cosmosdb_messages_container = cosmosdb_messages_container
    
    def create_conversations(self, user_id, summary):
        conversation = {
            'id': str(uuid.uuid4()),  
            'createdAt': datetime.utcnow().isoformat(),  
            'updatedAt': datetime.utcnow().isoformat(),  
            'userId': user_id,
            'summary': summary
        }
        self.cosmosdb_conversations_container.upsert_item(conversation)  
        return jsonify(conversation)
    
    def get_conversations(self, user_id):
        query = f'SELECT * FROM c WHERE ARRAY_CONTAINS(c.user, "{user_id}")'
        conversations = list(self.cosmosdb_conversations_container.query_items(query=query,
                                                                               enable_cross_partition_query =True))
        return jsonify(conversations)

    def create_message(self, conversation_id, user_id, text):
        message = {
            'id': str(uuid.uuid4()),  
            'conversationId': conversation_id,
            'userId': user_id,
            'messageText': text,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.cosmosdb_messages_container.upsert_item(message)  
        return jsonify(message)
    
    def get_messages(self, conversation_id, user_id):
        query = f'SELECT * FROM c WHERE c.conversationId = "{conversation_id}" AND c.userId = "{user_id}" ORDER BY c.timestamp ASC'
        messages = list(self.cosmosdb_messages_container.query_items(query=query,
                                                                     enable_cross_partition_query =True))
        return jsonify(messages)

