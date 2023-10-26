import io
import os
import re
from typing import Optional, Union

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.blob.aio import BlobServiceClient
from pypdf import PdfReader, PdfWriter

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

            # if file is PDF split into pages and upload each page as a separate blob
            if os.path.splitext(file.content.name)[1].lower() == ".pdf":
                with open(file.content.name, "rb") as reopened_file:
                    reader = PdfReader(reopened_file)
                    pages = reader.pages
                    for i in range(len(pages)):
                        blob_name = BlobManager.blob_name_from_file_page(file.content.name, i)
                        if self.verbose:
                            print(f"\tUploading blob for page {i} -> {blob_name}")
                        f = io.BytesIO()
                        writer = PdfWriter()
                        writer.add_page(pages[i])
                        writer.write(f)
                        f.seek(0)
                        await container_client.upload_blob(blob_name, f, overwrite=True)
            else:
                blob_name = BlobManager.blob_name_from_file_page(file.content.name, page=0)
                await container_client.upload_blob(blob_name, file.content, overwrite=True)

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
            async for b in blobs:
                if prefix is not None and not re.match(f"{prefix}-\d+\.pdf", b):
                    continue
                if self.verbose:
                    print(f"\tRemoving blob {b}")
                await container_client.delete_blob(b)

    @classmethod
    def blob_name_from_file_page(cls, filename, page=0) -> str:
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return os.path.splitext(os.path.basename(filename))[0] + f"-{page}" + ".pdf"
        else:
            return os.path.basename(filename)
