import base64
import hashlib
import logging
import os
import re
import tempfile
from abc import ABC
from glob import glob
from typing import IO, AsyncGenerator, Dict, List, Optional, Union

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.filedatalake.aio import (
    DataLakeServiceClient,
)
from azure.storage.blob.aio import BlobServiceClient, BlobClient

logger = logging.getLogger("scripts")


class File:
    """
    Represents a file stored either locally or in a data lake storage account
    This file might contain access control information about which users or groups can access it
    """

    def __init__(self, content: IO, acls: Optional[dict[str, list]] = None, url: Optional[str] = None):
        self.content = content
        self.acls = acls or {}
        self.url = url

    def filename(self):
        return os.path.basename(self.content.name)

    def file_extension(self):
        return os.path.splitext(self.content.name)[1]

    def filename_to_id(self):
        filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", self.filename())
        filename_hash = base64.b16encode(self.filename().encode("utf-8")).decode("ascii")
        acls_hash = ""
        if self.acls:
            acls_hash = base64.b16encode(str(self.acls).encode("utf-8")).decode("ascii")
        return f"file-{filename_ascii}-{filename_hash}{acls_hash}"

    def close(self):
        if self.content:
            self.content.close()


class ListFileStrategy(ABC):
    """
    Abstract strategy for listing files that are located somewhere. For example, on a local computer or remotely in a storage account
    """

    async def list(self) -> AsyncGenerator[File, None]:
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield

    async def list_paths(self) -> AsyncGenerator[str, None]:
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield


class LocalListFileStrategy(ListFileStrategy):
    """
    Concrete strategy for listing files that are located in a local filesystem
    """

    def __init__(self, path_pattern: str, force: bool = False):
        self.path_pattern = path_pattern
        self.force = force

    async def list_paths(self) -> AsyncGenerator[str, None]:
        async for p in self._list_paths(self.path_pattern):
            yield p

    async def _list_paths(self, path_pattern: str) -> AsyncGenerator[str, None]:
        for path in glob(path_pattern):
            if os.path.isdir(path):
                async for p in self._list_paths(f"{path}/*"):
                    yield p
            else:
                # Only list files, not directories
                yield path

    async def list(self) -> AsyncGenerator[File, None]:
        async for path in self.list_paths():
            if self.force or not self.check_md5(path):
                yield File(content=open(path, mode="rb"))

    def check_md5(self, path: str) -> bool:
        # if filename ends in .md5 skip
        if path.endswith(".md5"):
            return True

        # if there is a file called .md5 in this directory, see if its updated
        stored_hash = None
        with open(path, "rb") as file:
            existing_hash = hashlib.md5(file.read()).hexdigest()
        hash_path = f"{path}.md5"
        if os.path.exists(hash_path):
            with open(hash_path, encoding="utf-8") as md5_f:
                stored_hash = md5_f.read()

        if stored_hash and stored_hash.strip() == existing_hash.strip():
            logger.info("Skipping %s, no changes detected.", path)
            return True

        # Write the hash
        with open(hash_path, "w", encoding="utf-8") as md5_f:
            md5_f.write(existing_hash)

        return False


class ADLSGen2ListFileStrategy(ListFileStrategy):
    """
    Concrete strategy for listing files that are located in a data lake storage account
    """

    def __init__(
        self,
        data_lake_storage_account: str,
        data_lake_filesystem: str,
        data_lake_path: str,
        credential: Union[AsyncTokenCredential, str],
    ):
        self.data_lake_storage_account = data_lake_storage_account
        self.data_lake_filesystem = data_lake_filesystem
        self.data_lake_path = data_lake_path
        self.credential = credential

    async def list_paths(self) -> AsyncGenerator[str, None]:
        async with DataLakeServiceClient(
            account_url=f"https://{self.data_lake_storage_account}.dfs.core.windows.net", credential=self.credential
        ) as service_client, service_client.get_file_system_client(self.data_lake_filesystem) as filesystem_client:
            async for path in filesystem_client.get_paths(path=self.data_lake_path, recursive=True):
                if path.is_directory:
                    continue

                yield path.name

    async def list(self) -> AsyncGenerator[File, None]:
        async with DataLakeServiceClient(
            account_url=f"https://{self.data_lake_storage_account}.dfs.core.windows.net", credential=self.credential
        ) as service_client, service_client.get_file_system_client(self.data_lake_filesystem) as filesystem_client:
            async for path in self.list_paths():
                temp_file_path = os.path.join(tempfile.gettempdir(), os.path.basename(path))
                try:
                    async with filesystem_client.get_file_client(path) as file_client:
                        with open(temp_file_path, "wb") as temp_file:
                            downloader = await file_client.download_file()
                            await downloader.readinto(temp_file)
                    # Parse out user ids and group ids
                    acls: Dict[str, List[str]] = {"oids": [], "groups": []}
                    # https://learn.microsoft.com/python/api/azure-storage-file-datalake/azure.storage.filedatalake.datalakefileclient?view=azure-python#azure-storage-filedatalake-datalakefileclient-get-access-control
                    # Request ACLs as GUIDs
                    access_control = await file_client.get_access_control(upn=False)
                    acl_list = access_control["acl"]
                    # https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-access-control
                    # ACL Format: user::rwx,group::r-x,other::r--,user:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:r--
                    acl_list = acl_list.split(",")
                    for acl in acl_list:
                        acl_parts: list = acl.split(":")
                        if len(acl_parts) != 3:
                            continue
                        if len(acl_parts[1]) == 0:
                            continue
                        if acl_parts[0] == "user" and "r" in acl_parts[2]:
                            acls["oids"].append(acl_parts[1])
                        if acl_parts[0] == "group" and "r" in acl_parts[2]:
                            acls["groups"].append(acl_parts[1])
                    yield File(content=open(temp_file_path, "rb"), acls=acls, url=file_client.url)
                except Exception as data_lake_exception:
                    logger.error(f"\tGot an error while reading {path} -> {data_lake_exception} --> skipping file")
                    try:
                        os.remove(temp_file_path)
                    except Exception as file_delete_exception:
                        logger.error(f"\tGot an error while deleting {temp_file_path} -> {file_delete_exception}")

class BlobListFileStrategy:
    """
    Concrete strategy for listing files that are located in an Azure Blob Storage account
    """

    def __init__(
        self,
        storage_account: str,
        storage_container: str,
        credential: Union[AsyncTokenCredential, str],
        force: bool = False
    ):
        self.storage_account = storage_account
        self.storage_container = storage_container
        self.credential = credential
        self.temp_dir = './data'
        self.force = force

    async def list(self, path: Optional[str] = None) -> AsyncGenerator[File, None]:
        account_url = f"https://{self.storage_account}.blob.core.windows.net"
        async with BlobServiceClient(
            account_url=account_url, credential=self.credential
        ) as service_client, service_client.get_container_client(self.storage_container) as container_client:
            if not await container_client.exists():
                return

            prefix = os.path.splitext(os.path.basename(path))[0] if path else None
            blobs = container_client.list_blobs(name_starts_with=prefix)

            async for blob in blobs:
                # Ignore hash files
                if blob.name.endswith(".md5"):
                    continue

                logger.info("Found: %s", blob.name)

                async with BlobClient(
                    account_url=account_url,
                    container_name=self.storage_container,
                    blob_name=blob.name,
                    credential=self.credential,
                ) as blob_client:
                    # Check MD5 to determine if the blob has changed
                    if await self.check_md5(blob_client, blob.name) and self.force is False:
                        continue

                    # Create a temporary file to store the blob's content
                    temp_file_path = os.path.join(self.temp_dir, os.path.basename(blob.name))

                    # Download blob content to the temporary file
                    with open(temp_file_path, "wb") as file_stream:
                        stream = await blob_client.download_blob()
                        data = await stream.readall()
                        file_stream.write(data)

                    # Yield a File object with the downloaded content
                    yield File(content=open(temp_file_path, "rb"), url=f"{account_url}/{self.storage_container}/{blob.name}")

    async def check_md5(self, blob_client: BlobClient, blob_name: str) -> bool:
        # Retrieve blob properties
        properties = await blob_client.get_blob_properties()
        blob_md5 = properties.content_settings.content_md5

        if not blob_md5:
            return False  # If no MD5 hash is present, assume the blob has changed

        # Convert the MD5 to hex for comparison
        blob_md5_hex = base64.b16encode(blob_md5).decode("ascii")

        # Generate a client for the .md5 blob
        account_url = f"https://{self.storage_account}.blob.core.windows.net"
        hash_blob_name = f"{blob_name}.md5"
        async with BlobClient(
            account_url=account_url,
            container_name=self.storage_container,
            blob_name=hash_blob_name,
            credential=self.credential,
        ) as hash_blob_client:
            try:
                # Check if the .md5 file exists and retrieve its content
                stored_hash = await (await hash_blob_client.download_blob()).content_as_text()
                stored_hash = stored_hash.strip()
            except Exception:
                stored_hash = None

            if stored_hash == blob_md5_hex:
                logger.info("Skipping %s, no changes detected.", blob_name)
                return True

            # Upload the new hash to the .md5 file in the blob storage
            await hash_blob_client.upload_blob(blob_md5_hex, overwrite=True)

        return False