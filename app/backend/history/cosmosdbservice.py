import os
import uuid
from datetime import datetime
from flask import Flask, request
from azure.identity import DefaultAzureCredential  
from azure.cosmos import CosmosClient, PartitionKey  
  
class CosmosDbService():
    
    def __init__(self, cosmosdb_endpoint: str, cosmosdb_conversations_container: str, cosmosdb_messages_container: str):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.cosmosdb_conversations_container = cosmosdb_conversations_container
        self.cosmosdb_messages_container = cosmosdb_messages_container ## todo: remove the separate container, we'll just store messsages and conversations in the same container with a type field
    
    def create_conversation(self, user_id, title = ''):
        conversation = {
            'id': str(uuid.uuid4()),  
            'type': 'conversation',
            'createdAt': datetime.utcnow().isoformat(),  
            'updatedAt': datetime.utcnow().isoformat(),  
            'userId': user_id,
            'title': title
        }
        ## TODO: add some error handling based on the output of the upsert_item call
        resp = self.cosmosdb_conversations_container.upsert_item(conversation)  
        if resp:
            return resp
        else:
            return False
    
    def upsert_conversation(self, conversation):
        resp = self.cosmosdb_conversations_container.upsert_item(conversation)
        if resp:
            return resp
        else:
            return False

    def get_conversations(self, user_id, sort_order = 'DESC'):
        query = f"SELECT * FROM c where c.userId = '{user_id}' and c.type='conversation' order by c.updatedAt {sort_order}"
        conversations = list(self.cosmosdb_conversations_container.query_items(query=query,
                                                                               enable_cross_partition_query =True))
        ## if no conversations are found, return None
        if len(conversations) == 0:
            return None
        else:
            return conversations

    def get_conversation(self, user_id, conversation_id):
        query = f"SELECT * FROM c where c.id = '{conversation_id}' and c.type='conversation' and c.userId = '{user_id}'"
        conversation = list(self.cosmosdb_conversations_container.query_items(query=query,
                                                                               enable_cross_partition_query =True))
        ## if no conversations are found, return None
        if len(conversation) == 0:
            return None
        else:
            return conversation[0]
 
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
        if resp:
            ## update the parent conversations's updatedAt field with the current message's createdAt datetime value
            conversation = self.get_conversation(user_id, conversation_id)
            conversation['updatedAt'] = message['createdAt']
            self.upsert_conversation(conversation)
            return resp
        else:
            return False
    
    def get_messages(self, user_id, conversation_id):
        query = f"SELECT * FROM c WHERE c.conversationId = '{conversation_id}' AND c.type='message' AND c.userId = '{user_id}' ORDER BY c.timestamp ASC"
        messages = list(self.cosmosdb_conversations_container.query_items(query=query,
                                                                     enable_cross_partition_query =True))
        ## if no messages are found, return false
        if len(messages) == 0:
            return None
        else:
            return messages 

