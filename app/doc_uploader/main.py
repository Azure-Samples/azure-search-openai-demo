import datetime
from azure.storage.blob import BlobClient, generate_blob_sas, BlobSasPermissions, BlobServiceClient
from azure.core.utils import parse_connection_string
from fastapi import FastAPI
from azure.identity import DefaultAzureCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
from azure.mgmt.appcontainers.models import JobExecutionTemplate, JobExecutionContainer
import os
from azure.identity import DefaultAzureCredential

from fastapi.staticfiles import StaticFiles


app = FastAPI()


@app.get("/sas")
async def sas(filename: str):
    storage_account_name = os.environ["AZURE_STORAGE_ACCOUNT"]
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()

    current_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = current_time - datetime.timedelta(minutes=1)
    expiry_time = current_time + datetime.timedelta(days=1)

    blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
    account_key = blob_service_client.get_user_delegation_key(key_start_time=start_time, key_expiry_time=expiry_time)

    
    blob_name = filename
    container_name = "uploads"

    sas_token = generate_blob_sas(
        account_name=storage_account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(write=True),
        expiry=expiry_time,
        start=start_time
    )
    
    return {"sasUrl": f"{account_url}/{container_name}/{blob_name}?{sas_token}"}


@app.get("/startjob")
async def start_job():
    sub_id = ""
    client = ContainerAppsAPIClient(credential=DefaultAzureCredential(), subscription_id=sub_id)
    template = JobExecutionTemplate(
        containers = [
            {
                "image": "alpine",
                "name": "my-manual-job",
                "command":["sh", "-c", "echo 'hello from python'"],
                "resources":{
                    "cpu": 0.5,
                    "memory": "1Gi",
                }
            }
        ]
    )
    result = client.jobs.begin_start('jobs-ncusstage', 'my-manual-job4', template).result()
    return {"result": result}



app.mount("/", StaticFiles(directory="dist", html=True), name="dist")