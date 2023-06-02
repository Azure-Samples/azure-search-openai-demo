import os
import uuid
from datetime import datetime
from flask import Flask, request
from azure.identity import DefaultAzureCredential  
from azure.cosmos import CosmosClient, PartitionKey  
  
class CosmosConversationClient():
    
    def __init__(self, cosmosdb_endpoint: str, credential: any, database_name: str, container_name: str):
        self.cosmosdb_endpoint = cosmosdb_endpoint
        self.credential = credential
        self.database_name = database_name
        self.container_name = container_name
        self.cosmosdb_client = CosmosClient(self.cosmosdb_endpoint, credential=credential)
        self.database_client = self.cosmosdb_client.get_database_client(database_name)
        self.container_client = self.database_client.get_container_client(container_name)

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
        resp = self.container_client.upsert_item(conversation)  
        if resp:
            return resp
        else:
            return False
    
    def upsert_conversation(self, conversation):
        resp = self.container_client.upsert_item(conversation)
        if resp:
            return resp
        else:
            return False

    def delete_conversation(self, user_id, conversation_id):
        conversation = self.container_client.read_item(item=conversation_id, partition_key=user_id)        
        if conversation:
            print("Item exists")
            resp = self.container_client.delete_item(item=conversation_id, partition_key=user_id)
            return resp
        else:
            print("Item doesn't exist")
            return True

        
    def delete_messages(self, conversation_id, user_id):
        ## get a list of all the messages in the conversation
        messages = self.get_messages(user_id, conversation_id)
        response_list = []
        if messages:
            for message in messages:
                resp = self.container_client.delete_item(item=message['id'], partition_key=user_id)
                response_list.append(resp)
            return response_list


    def get_conversations(self, user_id, sort_order = 'DESC'):
        query = f"SELECT * FROM c where c.userId = '{user_id}' and c.type='conversation' order by c.updatedAt {sort_order}"
        conversations = list(self.container_client.query_items(query=query,
                                                                               enable_cross_partition_query =True))
        ## if no conversations are found, return None
        if len(conversations) == 0:
            return None
        else:
            return conversations

    def get_conversation(self, user_id, conversation_id):
        query = f"SELECT * FROM c where c.id = '{conversation_id}' and c.type='conversation' and c.userId = '{user_id}'"
        conversation = list(self.container_client.query_items(query=query,
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
        print(self.credential)
        
        resp = self.container_client.upsert_item(message)  
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
        messages = list(self.container_client.query_items(query=query,
                                                                     enable_cross_partition_query =True))
        ## if no messages are found, return false
        if len(messages) == 0:
            return None
        else:
            return messages

