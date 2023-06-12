import os
from azure.storage.blob import BlobServiceClient

AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER") or "content"

def get_blob_container(blob_credential):
    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", 
        credential=blob_credential
        )
    blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)
    return blob_container