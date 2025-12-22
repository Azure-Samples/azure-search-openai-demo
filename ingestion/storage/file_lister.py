"""
File listing strategies for document ingestion.

This module provides strategies for listing files from various sources
including local filesystem and Azure Data Lake Storage Gen2.
"""

import hashlib
import logging
import os
import tempfile
from abc import ABC
from collections.abc import AsyncGenerator

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.filedatalake.aio import DataLakeServiceClient

from ..models import File

logger = logging.getLogger("ingestion")


class ListFileStrategy(ABC):
    """
    Abstract strategy for listing files that are located somewhere.
    For example, on a local computer or remotely in a storage account.
    """

    async def list(self) -> AsyncGenerator[File, None]:
        """List files and yield File objects."""
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield

    async def list_paths(self) -> AsyncGenerator[str, None]:
        """List file paths."""
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield


class LocalListFileStrategy(ListFileStrategy):
    """
    Concrete strategy for listing files that are located in a local filesystem.
    """

    def __init__(self, path_pattern: str, enable_global_documents: bool = False):
        """
        Initialize the local file listing strategy.

        Args:
            path_pattern: Glob pattern for files to list (e.g., "data/*")
            enable_global_documents: Whether to mark files as globally accessible
        """
        self.path_pattern = path_pattern
        self.enable_global_documents = enable_global_documents

    async def list_paths(self) -> AsyncGenerator[str, None]:
        """List all file paths matching the pattern."""
        from glob import glob
        async for p in self._list_paths(self.path_pattern):
            yield p

    async def _list_paths(self, path_pattern: str) -> AsyncGenerator[str, None]:
        """Recursively list paths matching the pattern."""
        from glob import glob
        for path in glob(path_pattern):
            if os.path.isdir(path):
                async for p in self._list_paths(f"{path}/*"):
                    yield p
            else:
                yield path

    async def list(self) -> AsyncGenerator[File, None]:
        """List files and yield File objects, skipping unchanged files."""
        acls = {"oids": ["all"], "groups": ["all"]} if self.enable_global_documents else {}
        async for path in self.list_paths():
            if not self.check_md5(path):
                yield File(content=open(path, mode="rb"), acls=acls, url=path)

    def check_md5(self, path: str) -> bool:
        """Check if a file has changed since last processing using MD5 hash.

        Args:
            path: Path to the file

        Returns:
            True if file should be skipped (unchanged or is .md5 file)
        """
        if path.endswith(".md5"):
            return True

        stored_hash = None
        with open(path, "rb") as file:
            existing_hash = hashlib.md5(file.read()).hexdigest()
        hash_path = f"{path}.md5"
        if os.path.exists(hash_path):
            with open(hash_path, encoding="utf-8") as md5_f:
                stored_hash = md5_f.read()

        if stored_hash and stored_hash.strip() == existing_hash.strip():
            logger.info("Skipping '%s', no changes detected.", path)
            return True

        with open(hash_path, "w", encoding="utf-8") as md5_f:
            md5_f.write(existing_hash)

        return False


class ADLSGen2ListFileStrategy(ListFileStrategy):
    """
    Concrete strategy for listing files that are located in a data lake storage account.
    """

    def __init__(
        self,
        data_lake_storage_account: str,
        data_lake_filesystem: str,
        data_lake_path: str,
        credential: AsyncTokenCredential | str,
        enable_global_documents: bool = False,
    ):
        """
        Initialize the ADLS Gen2 file listing strategy.

        Args:
            data_lake_storage_account: Storage account name
            data_lake_filesystem: File system (container) name
            data_lake_path: Path within the file system
            credential: Authentication credential
            enable_global_documents: Whether to mark files as globally accessible
        """
        self.data_lake_storage_account = data_lake_storage_account
        self.data_lake_filesystem = data_lake_filesystem
        self.data_lake_path = data_lake_path
        self.credential = credential
        self.enable_global_documents = enable_global_documents

    async def list_paths(self) -> AsyncGenerator[str, None]:
        """List all file paths in the data lake."""
        async with DataLakeServiceClient(
            account_url=f"https://{self.data_lake_storage_account}.dfs.core.windows.net", credential=self.credential
        ) as service_client, service_client.get_file_system_client(self.data_lake_filesystem) as filesystem_client:
            async for path in filesystem_client.get_paths(path=self.data_lake_path, recursive=True):
                if path.is_directory:
                    continue
                yield path.name

    async def list(self) -> AsyncGenerator[File, None]:
        """List files and yield File objects with ACL information."""
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
                    acls: dict[str, list[str]] = {"oids": [], "groups": []}
                    access_control = await file_client.get_access_control(upn=False)
                    acl_list = access_control["acl"]
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

                    if self.enable_global_documents and len(acls["oids"]) == 0 and len(acls["groups"]) == 0:
                        acls = {"oids": ["all"], "groups": ["all"]}

                    yield File(content=open(temp_file_path, "rb"), acls=acls, url=file_client.url)
                except Exception as data_lake_exception:
                    logger.error(f"\tGot an error while reading {path} -> {data_lake_exception} --> skipping file")
                    try:
                        os.remove(temp_file_path)
                    except Exception as file_delete_exception:
                        logger.error(f"\tGot an error while deleting {temp_file_path} -> {file_delete_exception}")
