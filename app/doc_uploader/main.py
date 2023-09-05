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


@app.post("/startjob")
async def start_job(filename: str):
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
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )
    
    sas_url = f"{account_url}/{container_name}/{blob_name}?{sas_token}"

    # generate a log file name based on the timestamp
    log_file_name = f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

    sub_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    client = ContainerAppsAPIClient(credential=DefaultAzureCredential(), subscription_id=sub_id)
    template = client.jobs.get(os.environ["AZURE_RESOURCE_GROUP"], 'job-prepdocs').template
    env_vars = template.containers[0].env
    # find the env var named "BLOB_URL" and set its value to the filename
    for env_var in env_vars:
        if env_var.name == "BLOB_URL":
            env_var.value = sas_url
            print(f"Set BLOB_URL to {sas_url}")
        if env_var.name == "LOG_FILE_NAME":
            env_var.value = log_file_name
            print(f"Set LOG_FILE_NAME to {log_file_name}")
    
    result = client.jobs.begin_start(os.environ["AZURE_RESOURCE_GROUP"], 'job-prepdocs', template).result()
    print(result)

    logs_sas_token = generate_blob_sas(
        account_name=storage_account_name,
        container_name="prepdocslogs",
        blob_name=log_file_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )

    logs_sas_url = f"{account_url}/prepdocslogs/{log_file_name}?{logs_sas_token}"
    return {
        "result": result,
        "logFileUrl": logs_sas_url
    }



app.mount("/", StaticFiles(directory="dist", html=True), name="dist")