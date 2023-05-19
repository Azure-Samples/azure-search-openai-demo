import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential  
from azure.cosmos import CosmosClient, PartitionKey  
  
class CosmosDbService():
    
    def __init__(self, cosmosdb_endpoint: str, cosmosdb_conversations_container: str, cosmosdb_messages_container: str):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.cosmosdb_conversations_container = cosmosdb_conversations_container
        self.cosmosdb_messages_container = cosmosdb_messages_container ## todo: remove the separate container, we'll just store messsages and conversations in the same container with a type field
    
    def create_conversations(self, user_id, summary = ''):
        conversation = {
            'id': str(uuid.uuid4()),  
            'type': 'conversation',
            'createdAt': datetime.utcnow().isoformat(),  
            'updatedAt': datetime.utcnow().isoformat(),  
            'userId': user_id,
            'summary': summary
        }
        ## TODO: add some error handling based on the output of the upsert_item call
        self.cosmosdb_conversations_container.upsert_item(conversation)  
        return conversation
    
    def get_conversations(self, user_id):
        query = f"SELECT * FROM c where c.userId = '{user_id}' and c.type='conversation' order by c.timestamp ASC"
        conversations = list(self.cosmosdb_conversations_container.query_items(query=query,
                                                                               enable_cross_partition_query =True))
        return conversations

    def create_message(self, conversation_id, user_id, input_message: dict):
        message = {
            'id': str(uuid.uuid4()),
            'type': 'message',
            'userId' : user_id,
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'conversationId' : conversation_id,
            'role': input_message['role'],
            'content': input_message['content']
        }
        
        resp = self.cosmosdb_conversations_container.upsert_item(message)  
        return message
    
    def get_messages(self, conversation_id, user_id):
        query = f"SELECT * FROM c WHERE c.conversationId = '{conversation_id}' AND type='message' AND c.userId = '{user_id}' ORDER BY c.timestamp ASC"
        messages = list(self.cosmosdb_conversations_container.query_items(query=query,
                                                                     enable_cross_partition_query =True))
        return messages

