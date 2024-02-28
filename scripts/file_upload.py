import streamlit as st
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

# Azure Storage account credentials
AZURE_STORAGE_CONNECTION_STRING = "YOUR_AZURE_STORAGE_CONNECTION_STRING"
CONTAINER_NAME = "YOUR_CONTAINER_NAME"

# Connect to the Azure Blob Storage
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Azure Search OpenAI Demo
st.title("Azure Search OpenAI Demo")

# File uploader
uploaded_file = st.file_uploader("Upload a file", type=['txt'])

if uploaded_file is not None:
    # Upload the file to Azure Blob Storage
    blob_client = container_client.get_blob_client(uploaded_file.name)
    blob_client.upload_blob(uploaded_file)

    st.write("File uploaded successfully.")