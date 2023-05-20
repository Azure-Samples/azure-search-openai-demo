import os
import mimetypes
import time
import logging
import openai
import json
from datetime import datetime
from history.cosmosdbservice import CosmosDbService
from auth.auth_utils import get_authenticated_user_details
from azure.cosmos import CosmosClient, PartitionKey

from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.readretrieveread import ReadRetrieveReadApproach
from approaches.readdecomposeask import ReadDecomposeAsk
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.chatconversation import ChatConversationReadApproach
from azure.storage.blob import BlobServiceClient

## Logging level for development, set to logging.INFO or logging.DEBUG for more verbose logging
logger = logging.getLogger ('werkzeug') # grabs underlying WSGI logger
logger.setLevel (logging.INFO) # set log level to INFO

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER") or "content"
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX") or "gptkbindex"
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION") or "2023-05-15"
AZURE_COSMOSDB_DATABASE = os.environ.get("AZURE_COSMOSDB_DATABASE") or "db_conversation_history"
AZURE_COSMOSDB_ACCOUNT = os.environ.get("AZURE_COSMOSDB_ACCOUNT")
AZURE_COSMOSDB_CONVERSATIONS_CONTAINER = os.environ.get("AZURE_COSMOSDB_CONVERSATIONS_CONTAINER") or "conversations"
AZURE_COSMOSDB_MESSAGES_CONTAINER = os.environ.get("AZURE_COSMOSDB_MESSAGES_CONTAINER") or "messages"

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed, 
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the 
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential()

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = AZURE_OPENAI_API_VERSION

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)
blob_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", 
    credential=azure_credential)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

# Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
# or some derivative, here we include several for exploration purposes
ask_approaches = {
    "rtr": RetrieveThenReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rrr": ReadRetrieveReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rda": ReadDecomposeAsk(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)  
}
## BDL: added another set of approaches for vanilla chatgpt
chatconversation_approaches = {
    'chatconversation': ChatConversationReadApproach(AZURE_OPENAI_CHATGPT_DEPLOYMENT)
}

# Initialize a CosmosDB client with AAD auth and containers
cosmos_endpoint = f'https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/'
cosmos_client = CosmosClient(cosmos_endpoint, credential=azure_credential)
database = cosmos_client.get_database_client(AZURE_COSMOSDB_DATABASE)
conversations_container = database.get_container_client(AZURE_COSMOSDB_CONVERSATIONS_CONTAINER)
messages_container = database.get_container_client(AZURE_COSMOSDB_MESSAGES_CONTAINER)
## Initialize CosmosDbService object
cosmos = CosmosDbService(cosmos_endpoint, conversations_container, messages_container)

app = Flask(__name__)

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)

# Serve content files from blob storage from within the app to keep the example self-contained. 
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@app.route("/content/<path>")
def content_file(path):
    blob = blob_container.get_blob_client(path).download_blob()
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return blob.readall(), 200, {"Content-Type": mime_type, "Content-Disposition": f"inline; filename={path}"}
    
@app.route("/ask", methods=["POST"])
def ask():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = ask_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["question"], request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /ask")
        return jsonify({"error": str(e)}), 500

## BDL: this is the original chat function
@app.route("/chat", methods=["POST"])
def chat():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["history"], request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500


## BDL: method for creating conversations and storing history messages in cosmos
@app.route("/conversation/add", methods=["POST"])
def add_conversation():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ensure_openai_token()
    
    approach = request.json["approach"]
    
    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)

    try:
        impl = chatconversation_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        ## BDL TODO: should all of this conversation history be moved to the parent "approach" class so it can be shared across all approaches?
        # check for the conversation_id, if the conversation is not set, we will create a new one
        if not conversation_id:
            conversation_dict = cosmos.create_conversation(user_id=user_id)
            conversation_id = conversation_dict['id']
            
        ## Format the incoming message object in the "chat/completions" messages format
        ## then write it to the conversation history in cosmos
        message_prompt = request.json["history"][-1]["user"]
        msg = {"role": "user", "content": message_prompt}
        resp = cosmos.create_message(
            conversation_id=conversation_id,
            user_id=user_id,
            input_message=msg
        )

        # Submit prompt to Chat Completions for response
        r = impl.run(request.json["history"], request.json.get("overrides") or {})
        
        ## Format the incoming message object in the "chat/completions" messages format
        ## then write it to the conversation history in cosmos
        msg = {"role": "assistant", "content": r['answer']}
        resp = cosmos.create_message(
            conversation_id=conversation_id,
            user_id=user_id,
            input_message=msg
        )
        
        ## we need to return the conversation_id in the response so the client can keep track of it
        r['conversation_id'] = conversation_id
        # returns the response from the bot
        return jsonify(r)
       
    except Exception as e:
        logging.exception("Exception in /conversation")
        return jsonify({"error": str(e)}), 500

## Conversation routes needed read, delete, update
@app.route("/conversation/delete", methods=["POST"])
def delete_conversation(conversation_id: None):
    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    return jsonify({"error": "not implemented"}), 501

@app.route("/conversation/update", methods=["POST"])
def update_conversation():
    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    return jsonify({"error": "not implemented"}), 501

@app.route("/conversation/list", methods=["POST"])
def list_conversations():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## get the conversations from cosmos
    conversations = cosmos.get_conversations(user_id)
    if not conversations:
        return jsonify({"error": f"No conversations for {user_id} were found"}), 404

    ## return the conversation ids

    return jsonify(conversations), 200

@app.route("/conversation/read", methods=["POST"])
def get_conversation():
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)
    
    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    ## get the conversation object and the related messages from cosmos
    conversation = cosmos.get_conversation(user_id, conversation_id)
    ## return the conversation id and the messages in the bot frontend format
    if not conversation:
        return jsonify({"error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."}), 404
    
    # get the messages for the conversation from cosmos
    conversation_messages = cosmos.get_messages(user_id, conversation_id)
    if not conversation_messages:
        return jsonify({"error": f"No messages for {conversation_id} were found"}), 404

    ## format the messages in the bot frontend format
    messages = format_messages(conversation_messages, input_format='cosmos', output_format='botfrontend')

    return jsonify({"conversation_id": conversation_id, "messages": messages}), 200

## add a route to generate a title for a conversation
@app.route("/conversation/gen_title", methods=["POST"])
def gen_title():
    ## lookup the conversation in cosmos
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user['user_principal_id']

    ## check request for conversation_id
    conversation_id = request.json.get("conversation_id", None)

    ## get the conversation from cosmos
    conversation_dict = cosmos.get_conversation(user_id, conversation_id)
    if not conversation_dict:
        return jsonify({"error": f"Conversation {conversation_id} not found"}), 404

    ## check if the conversation already has a title
    conversation_title = conversation_dict.get('title', None)
    
    overwrite_existing_title = request.json.get("overwrite_existing_title", False)
    if not overwrite_existing_title and conversation_title:
        return jsonify({"warning": f"Conversation {conversation_id} already has a title"}), 200

    ## otherwise go for it and create the title! 
    ## get the messages for the conversation from cosmos
    conversation_messages = cosmos.get_messages(user_id, conversation_id)
    if not conversation_messages:
        return jsonify({"error": f"No messages for {conversation_id} were found"}), 404

    ## generate a title for the conversation
    title = create_conversation_title(conversation_messages)
    conversation_dict['title'] = title
    conversation_dict['updatedAt'] = datetime.utcnow().isoformat()

    ## update the conversation in cosmos
    resp = cosmos.upsert_conversation(conversation_dict)

    if resp:
        return jsonify(conversation_dict)
    else:
        return jsonify({"error": f"Error updating conversation {conversation_id}: {conversation_dict}"}), 500


def create_conversation_title(conversation_messages):
    ## make sure the messages are sorted by _ts descending
    messages = format_messages(conversation_messages, input_format='cosmos' ,output_format='chatcompletions')

    title_prompt = 'Summarize the conversation so far into a 4-word or less title. Do not use any quotation marks or punctuation. Respond with a json object in the format {{"title": string}}. Do not include any other commentary or description.'

    messages.append({'role': 'user', 'content': title_prompt})

    ensure_openai_token()

    try:
        ## Submit prompt to Chat Completions for response
        completion = openai.ChatCompletion.create(    
            engine=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            messages=messages,
            temperature=1,
            max_tokens=64 
        )
        title = json.loads(completion['choices'][0]['message']['content'])['title']

        return title
    except Exception as e:
        return jsonify({"error": f"Error generating title for the conversation: {e}"}), 500

def format_messages(messages, input_format='cosmos', output_format='chatcompletions'):

    if input_format == 'cosmos': 
        ## Convert to the chat/completions format
        if output_format == 'chatcompletions':
            chat_messages = [{'role': msg['role'], 'content': msg['content']} for msg in messages]
            return chat_messages
        ## Convert to the bot frontend format
        elif output_format == 'botfrontend':
            ## the botfrontend format is pairs of {"user": inputtext, "bot": outputtext}
            ## the cosmos format is a list of messages with a role and content.
            ## form pairs of user and bot messages from the cosmos messages list 

            botfrontend_messages = []
            for message in messages:
                if message['role'] == 'user':
                    botfrontend_messages.append({"user": message['content']})
                elif message['role'] == 'assistant':
                    botfrontend_messages[-1]["bot"] = message['content']

            return botfrontend_messages

def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
    
if __name__ == "__main__":
    app.run()
