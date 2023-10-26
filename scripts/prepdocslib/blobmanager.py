import os
import re
from typing import Optional, Union

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.blob.aio import BlobServiceClient

from .listfilestrategy import File


class BlobManager:
    """
    Class to manage uploading and deleting blobs containing citation information from a blob storage account
    """

    def __init__(
        self,
        endpoint: str,
        container: str,
        credential: Union[AsyncTokenCredential, str],
        verbose: bool = False,
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.container = container
        self.verbose = verbose

    async def upload_blob(self, file: File):
        async with BlobServiceClient(
            account_url=self.endpoint, credential=self.credential
        ) as service_client, service_client.get_container_client(self.container) as container_client:
            if not await container_client.exists():
                await container_client.create_container()

            # Re-open and upload the original file
            with open(file.content.name, "rb") as reopened_file:
                blob_name = BlobManager.blob_name_from_file_name(file.content.name)
                print(f"\tUploading blob for whole file -> {blob_name}")
                await container_client.upload_blob(blob_name, reopened_file, overwrite=True)

    async def remove_blob(self, path: Optional[str] = None):
        async with BlobServiceClient(
            account_url=self.endpoint, credential=self.credential
        ) as service_client, service_client.get_container_client(self.container) as container_client:
            if not await container_client.exists():
                return
            if path is None:
                prefix = None
                blobs = container_client.list_blob_names()
            else:
                prefix = os.path.splitext(os.path.basename(path))[0]
                blobs = container_client.list_blob_names(name_starts_with=os.path.splitext(os.path.basename(prefix))[0])
            async for blob_path in blobs:
                # This still supports PDFs split into individual pages, but we could remove in future to simplify code
                if (prefix is not None and not re.match(rf"{prefix}-\d+\.pdf", blob_path)) or (
                    path is not None and blob_path == os.path.basename(path)
                ):
                    continue
                if self.verbose:
                    print(f"\tRemoving blob {blob_path}")
                await container_client.delete_blob(blob_path)

    @classmethod
    def sourcepage_from_file_page(cls, filename, page=0) -> str:
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return f"{os.path.basename(filename)}#page={page+1}"
        else:
            return os.path.basename(filename)

    @classmethod
    def blob_name_from_file_name(cls, filename) -> str:
        return os.path.basename(filename)
