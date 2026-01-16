import base64
import hashlib
import logging
import os
import re
from abc import ABC
from collections.abc import AsyncGenerator
from glob import glob
from typing import IO, Optional

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

    def filename(self) -> str:
        """
        Get the filename from the content object.

        Different file-like objects store the filename in different attributes:
        - File objects from open() have a .name attribute
        - HTTP uploaded files (werkzeug.datastructures.FileStorage) have a .filename attribute

        Returns:
            str: The basename of the file
        """
        content_name = None

        # Try to get filename attribute (common for HTTP uploaded files)
        if hasattr(self.content, "filename"):
            content_name = getattr(self.content, "filename")
            if content_name:
                return os.path.basename(content_name)

        # Try to get name attribute (common for file objects from open())
        if hasattr(self.content, "name"):
            content_name = getattr(self.content, "name")
            if content_name and content_name != "file":
                return os.path.basename(content_name)

        raise ValueError("The content object does not have a filename or name attribute. ")

    def file_extension(self):
        return os.path.splitext(self.filename())[1]

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

    def __init__(self, path_pattern: str, enable_global_documents: bool = False):
        self.path_pattern = path_pattern
        self.enable_global_documents = enable_global_documents

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
        acls = {"oids": ["all"], "groups": ["all"]} if self.enable_global_documents else {}
        async for path in self.list_paths():
            if not self.check_md5(path):
                yield File(content=open(path, mode="rb"), acls=acls, url=path)

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
            logger.info("Skipping '%s', no changes detected.", path)
            return True

        # Write the hash
        with open(hash_path, "w", encoding="utf-8") as md5_f:
            md5_f.write(existing_hash)

        return False
