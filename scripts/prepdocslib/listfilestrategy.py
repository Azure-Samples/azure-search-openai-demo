import hashlib
import os
import tempfile
from abc import ABC
from glob import glob
from typing import AsyncGenerator, Dict, List, Union

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.filedatalake.aio import (
    DataLakeServiceClient,
)

from .blobmanager import BlobManager


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

    def __init__(self, path_pattern: str, verbose: bool = False):
        self.path_pattern = path_pattern
        self.verbose = verbose

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
            if not self.check_md5(path):
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
            if self.verbose:
                print(f"Skipping {path}, no changes detected.")
            return True

        # Write the hash
        with open(hash_path, "w", encoding="utf-8") as md5_f:
            md5_f.write(existing_hash)

        return False


class BlobListFileStrategy(ListFileStrategy):
    """
    Concrete strategy for listing remote files that are located in a blob storage account
    """

    def __init__(self, path_pattern: str, blob_manager: BlobManager, verbose: bool = False):
        self.path_pattern = path_pattern
        self.blob_manager = blob_manager
        self.verbose = verbose

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
            if not await self.check_md5(path):
                yield File(content=open(path, mode="rb"))

    async def check_md5(self, path: str) -> bool:
        # if filename ends in .md5 skip
        if path.endswith(".md5"):
            return True

        # get hash from local file
        with open(path, "rb") as file:
            existing_hash = hashlib.md5(file.read()).hexdigest()

        # get hash from blob storage
        blob_hash = await self.blob_manager.get_blob_hash(os.path.basename(path))

        # compare hashes from local and blob storage
        if blob_hash and blob_hash.strip() == existing_hash.strip():
            if self.verbose:
                print(f"Skipping {path}, no changes detected.")
            return True

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
        verbose: bool = False,
    ):
        self.data_lake_storage_account = data_lake_storage_account
        self.data_lake_filesystem = data_lake_filesystem
        self.data_lake_path = data_lake_path
        self.credential = credential
        self.verbose = verbose

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
                    yield File(content=open(temp_file_path, "rb"), acls=acls)
                except Exception as data_lake_exception:
                    print(f"\tGot an error while reading {path} -> {data_lake_exception} --> skipping file")
                    try:
                        os.remove(temp_file_path)
                    except Exception as file_delete_exception:
                        print(f"\tGot an error while deleting {temp_file_path} -> {file_delete_exception}")
