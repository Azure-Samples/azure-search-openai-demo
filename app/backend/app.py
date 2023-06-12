import os
import mimetypes
import time
import logging
from flask import Flask, request, jsonify
import openai
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

# load sys env variables
from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

# load own moduls from this point
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.readretrieveread import ReadRetrieveReadApproach
from approaches.readdecomposeask import ReadDecomposeAsk
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from lib.link_attatcher import LinkAttatcher
from lib.tripadvisor import TripAdvisorClient
import search
import storage

# nesessary fo the connection with the backend services in case of using api keys
DEVELOPMENT = os.environ.get("environment") == "development"

CLIENT_ID=os.environ.get("CLIENT_ID")
CLIENT_SECRET=os.environ.get("CLIENT_SECRET")

AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"

AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY")
AZURE_BLOB_KEY = os.environ.get("AZURE_BLOB_KEY")
TRIPADVISOR_API_KEY = os.environ.get("TRIPADVISOR_API_KEY")


# App creation 
app = Flask(__name__)
app.config["CLIENT_ID"] = CLIENT_ID
app.config["CLIENT_SECRET"] = CLIENT_SECRET

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed, 
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the 
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = None if AZURE_SEARCH_KEY and AZURE_BLOB_KEY and AZURE_OPENAI_KEY else DefaultAzureCredential()

# Config openai client
openai.api_type = "azure" if AZURE_OPENAI_KEY else "azure_ad"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2023-03-15-preview"

if not AZURE_OPENAI_KEY:
    openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
    openai.api_key = openai_token.token
else:
    openai.api_key = AZURE_OPENAI_KEY


# Set up external services
search_client = search.get_client(AzureKeyCredential(AZURE_SEARCH_KEY) if AZURE_SEARCH_KEY else azure_credential)
blob_container = storage.get_blob_container(None if AZURE_BLOB_KEY else azure_credential)

# Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
# or some derivative, here we include several for exploration purposes
ask_approaches = {
    "rtr": RetrieveThenReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, search.KB_FIELDS_SOURCEPAGE, search.KB_FIELDS_CONTENT),
    "rrr": ReadRetrieveReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, search.KB_FIELDS_SOURCEPAGE, search.KB_FIELDS_CONTENT),
    "rda": ReadDecomposeAsk(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, search.KB_FIELDS_SOURCEPAGE, search.KB_FIELDS_CONTENT)
}

chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_GPT_DEPLOYMENT, search.KB_FIELDS_SOURCEPAGE, search.KB_FIELDS_CONTENT)
}


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
    
@app.route("/chat", methods=["POST"])
def chat():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["history"], request.json.get("overrides") or {})
        middleware = LinkAttatcher(TripAdvisorClient(TRIPADVISOR_API_KEY), AZURE_OPENAI_GPT_DEPLOYMENT)
        r["answer"] = middleware.attatch_links(r["answer"])
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500

def ensure_openai_token():
    if AZURE_OPENAI_KEY:
        print("XDXD")
        return True
    else:
        global openai_token
        if openai_token.expires_on < int(time.time()) - 60:
            openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
            openai.api_key = openai_token.token

if __name__ == "__main__":
    app.run()
