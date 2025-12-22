"""
Azure Blob Storage management for document ingestion.

This module provides classes for uploading, downloading, and managing
documents and images in Azure Blob Storage and Azure Data Lake Storage Gen2.
"""

import io
import logging
import os
import re
from pathlib import Path
from typing import IO, Any, Optional, TypedDict
from urllib.parse import unquote

from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.filedatalake.aio import (
    DataLakeDirectoryClient,
    FileSystemClient,
)
from PIL import Image, ImageDraw, ImageFont

from ..models import File

logger = logging.getLogger("ingestion")


class BlobProperties(TypedDict, total=False):
    """Properties of a blob, with optional fields for content settings."""
    content_settings: dict[str, Any]


class BaseBlobManager:
    """
    Base class for Azure Storage operations, providing common file naming and path utilities.
    """

    @classmethod
    def sourcepage_from_file_page(cls, filename: str, page: int = 0) -> str:
        """Generate a source page reference from filename and page number.

        Args:
            filename: The document filename
            page: 0-indexed page number

        Returns:
            Source page reference string (e.g., "doc.pdf#page=1")
        """
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return f"{os.path.basename(filename)}#page={page+1}"
        else:
            return os.path.basename(filename)

    @classmethod
    def blob_name_from_file_name(cls, filename: str) -> str:
        """Extract blob name from a file path."""
        return os.path.basename(filename)

    @classmethod
    def add_image_citation(
        cls, image_bytes: bytes, document_filename: str, image_filename: str, page_num: int
    ) -> bytes:
        """
        Adds citation text to an image from a document.

        Args:
            image_bytes: The original image bytes
            document_filename: The name of the document containing the image
            image_filename: The name of the image file
            page_num: The page number where the image appears

        Returns:
            Modified image bytes with citation text added
        """
        image = Image.open(io.BytesIO(image_bytes))
        line_height = 30
        text_height = line_height * 2
        new_img = Image.new("RGB", (image.width, image.height + text_height), "white")
        new_img.paste(image, (0, text_height))

        draw = ImageDraw.Draw(new_img)
        sourcepage = cls.sourcepage_from_file_page(document_filename, page=page_num)
        text = sourcepage
        figure_text = image_filename

        # Load the Jupiteroid font - look in multiple locations
        font_path = Path(__file__).parent.parent.parent / "prepdocslib" / "Jupiteroid-Regular.ttf"
        if not font_path.exists():
            font_path = Path(__file__).parent / "Jupiteroid-Regular.ttf"
        
        try:
            font = ImageFont.truetype(str(font_path), 20)
        except OSError:
            font = ImageFont.load_default()

        fig_width = draw.textlength(figure_text, font=font)

        padding = 20
        draw.text((padding, 5), text, font=font, fill="black")
        draw.text(
            (new_img.width - fig_width - padding, line_height + 5), figure_text, font=font, fill="black"
        )

        output = io.BytesIO()
        format = image.format or "PNG"
        new_img.save(output, format=format)

        return output.getvalue()

    async def upload_document_image(
        self,
        document_filename: str,
        image_bytes: bytes,
        image_filename: str,
        image_page_num: int,
        user_oid: Optional[str] = None,
    ) -> Optional[str]:
        """Upload a document image to storage."""
        raise NotImplementedError("Subclasses must implement this method")

    async def download_blob(
        self, blob_path: str, user_oid: Optional[str] = None
    ) -> Optional[tuple[bytes, BlobProperties]]:
        """Download a blob from storage."""
        raise NotImplementedError("Subclasses must implement this method")


class AdlsBlobManager(BaseBlobManager):
    """
    Manager for Azure Data Lake Storage blob operations, particularly for user-specific file operations.
    Documents are stored directly in the user's directory for backwards compatibility.
    Images are stored in a separate images subdirectory for better organization.
    """

    def __init__(self, endpoint: str, container: str, credential: AsyncTokenCredential):
        """
        Initialize the AdlsBlobManager.

        Args:
            endpoint: The ADLS endpoint URL
            container: The name of the container (file system)
            credential: The credential for accessing ADLS
        """
        self.endpoint = endpoint
        self.container = container
        self.credential = credential
        self.file_system_client = FileSystemClient(
            account_url=self.endpoint,
            file_system_name=self.container,
            credential=self.credential,
        )

    async def close_clients(self):
        """Close the file system client."""
        await self.file_system_client.close()

    async def _ensure_directory(self, directory_path: str, user_oid: str) -> DataLakeDirectoryClient:
        """Ensure a directory exists with proper permissions."""
        directory_client = self.file_system_client.get_directory_client(directory_path)
        try:
            await directory_client.get_directory_properties()
            props = await directory_client.get_access_control()
            if props.get("owner") != user_oid:
                raise PermissionError(f"User {user_oid} does not have permission to access {directory_path}")
        except ResourceNotFoundError:
            logger.info("Creating directory path %s", directory_path)
            await directory_client.create_directory()
            await directory_client.set_access_control(owner=user_oid)
        return directory_client

    async def upload_blob(self, file: File | IO, filename: str, user_oid: str) -> str:
        """Upload a file to the user's directory in ADLS."""
        user_directory_client = await self._ensure_directory(directory_path=user_oid, user_oid=user_oid)
        file_client = user_directory_client.get_file_client(filename)

        if isinstance(file, File):
            file_io = file.content
        else:
            file_io = file

        file_io.seek(0)
        await file_client.upload_data(file_io, overwrite=True)
        file_io.seek(0)

        return unquote(file_client.url)

    def _get_image_directory_path(self, document_filename: str, user_oid: str, page_num: Optional[int] = None) -> str:
        """Get the standardized path for storing document images."""
        if page_num is not None:
            return f"{user_oid}/images/{document_filename}/page_{page_num}"
        return f"{user_oid}/images/{document_filename}"

    async def upload_document_image(
        self,
        document_filename: str,
        image_bytes: bytes,
        image_filename: str,
        image_page_num: int,
        user_oid: Optional[str] = None,
    ) -> Optional[str]:
        """Upload an image from a document to ADLS."""
        if user_oid is None:
            raise ValueError("user_oid must be provided for user-specific operations.")
        await self._ensure_directory(directory_path=user_oid, user_oid=user_oid)
        image_directory_path = self._get_image_directory_path(document_filename, user_oid, image_page_num)
        image_directory_client = await self._ensure_directory(directory_path=image_directory_path, user_oid=user_oid)
        file_client = image_directory_client.get_file_client(image_filename)
        image_bytes = BaseBlobManager.add_image_citation(image_bytes, document_filename, image_filename, image_page_num)
        logger.info("Uploading document image '%s' to '%s'", image_filename, image_directory_path)
        await file_client.upload_data(image_bytes, overwrite=True, metadata={"UploadedBy": user_oid})
        return unquote(file_client.url)

    async def download_blob(
        self, blob_path: str, user_oid: Optional[str] = None
    ) -> Optional[tuple[bytes, BlobProperties]]:
        """Download a blob from Azure Data Lake Storage."""
        if user_oid is None:
            logger.warning("user_oid must be provided for Data Lake Storage operations.")
            return None

        path_parts = blob_path.split("/")
        if len(path_parts) < 2:
            filename = blob_path
            directory_path = user_oid
        else:
            root_dir = path_parts[0]
            if root_dir != user_oid:
                logger.warning(f"User {user_oid} does not have permission to access {blob_path}")
                return None
            directory_path = "/".join(path_parts[:-1])
            filename = path_parts[-1]

        try:
            user_directory_client = await self._ensure_directory(directory_path=directory_path, user_oid=user_oid)
            file_client = user_directory_client.get_file_client(filename)
            download_response = await file_client.download_file()
            content = await download_response.readall()

            properties: BlobProperties = {
                "content_settings": {
                    "content_type": download_response.properties.get("content_type", "application/octet-stream")
                }
            }

            return content, properties
        except ResourceNotFoundError:
            logger.warning(f"Directory or file not found: {directory_path}/{filename}")
            return None
        except Exception as e:
            logging.error(f"Error accessing directory {directory_path}: {str(e)}")
            return None

    async def remove_blob(self, filename: str, user_oid: str) -> None:
        """Delete a file and its associated images from ADLS."""
        user_directory_client = await self._ensure_directory(directory_path=user_oid, user_oid=user_oid)
        file_client = user_directory_client.get_file_client(filename)
        await file_client.delete_file()

        image_directory_path = self._get_image_directory_path(filename, user_oid)
        try:
            image_directory_client = await self._ensure_directory(
                directory_path=image_directory_path, user_oid=user_oid
            )
            await image_directory_client.delete_directory()
            logger.info(f"Deleted associated image directory: {image_directory_path}")
        except ResourceNotFoundError:
            logger.debug(f"No image directory found at {image_directory_path}")
            pass

    async def list_blobs(self, user_oid: str) -> list[str]:
        """List uploaded documents for the given user."""
        await self._ensure_directory(directory_path=user_oid, user_oid=user_oid)
        files = []
        try:
            all_paths = self.file_system_client.get_paths(path=user_oid, recursive=True)
            async for path in all_paths:
                path_parts = path.name.split("/", 1)
                if len(path_parts) != 2:
                    continue

                filename = path_parts[1]
                if (
                    "/" not in filename
                    and not any(filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"])
                    and "images" not in filename
                ):
                    files.append(filename)
        except ResourceNotFoundError as error:
            if error.status_code != 404:
                logger.exception("Error listing uploaded files", error)
        return files


class BlobManager(BaseBlobManager):
    """
    Class to manage uploading and deleting blobs containing citation information from a blob storage account.
    """

    def __init__(
        self,
        endpoint: str,
        container: str,
        credential: AsyncTokenCredential | str,
        image_container: Optional[str] = None,
        account: Optional[str] = None,
        resource_group: Optional[str] = None,
        subscription_id: Optional[str] = None,
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.account = account
        self.container = container
        self.resource_group = resource_group
        self.subscription_id = subscription_id
        self.image_container = image_container
        self.blob_service_client = BlobServiceClient(
            account_url=self.endpoint, credential=self.credential, max_single_put_size=4 * 1024 * 1024
        )

    async def close_clients(self):
        """Close the blob service client."""
        await self.blob_service_client.close()

    def get_managedidentity_connectionstring(self) -> str:
        """Get the managed identity connection string for the storage account."""
        if not self.account or not self.resource_group or not self.subscription_id:
            raise ValueError("Account, resource group, and subscription ID must be set to generate connection string.")
        return f"ResourceId=/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.Storage/storageAccounts/{self.account};"

    async def upload_blob(self, file: File) -> str:
        """Upload a file to blob storage."""
        container_client = self.blob_service_client.get_container_client(self.container)
        if not await container_client.exists():
            await container_client.create_container()

        if file.url is None or os.path.exists(file.url):
            with open(file.content.name, "rb") as reopened_file:
                blob_name = self.blob_name_from_file_name(file.content.name)
                logger.info("Uploading blob for document '%s'", blob_name)
                blob_client = await container_client.upload_blob(blob_name, reopened_file, overwrite=True)
                file.url = blob_client.url

        if file.url is None:
            raise ValueError("file.url must be set after upload")
        return unquote(file.url)

    async def upload_document_image(
        self,
        document_filename: str,
        image_bytes: bytes,
        image_filename: str,
        image_page_num: int,
        user_oid: Optional[str] = None,
    ) -> Optional[str]:
        """Upload a document image to blob storage."""
        if self.image_container is None:
            raise ValueError(
                "Image container name is not set. Re-run `azd provision` to automatically set up the images container."
            )
        if user_oid is not None:
            raise ValueError(
                "user_oid is not supported for BlobManager. Use AdlsBlobManager for user-specific operations."
            )
        container_client = self.blob_service_client.get_container_client(self.image_container)
        if not await container_client.exists():
            await container_client.create_container()
        image_bytes = self.add_image_citation(image_bytes, document_filename, image_filename, image_page_num)
        blob_name = f"{self.blob_name_from_file_name(document_filename)}/page{image_page_num}/{image_filename}"
        logger.info("Uploading blob for document image '%s'", blob_name)
        blob_client = await container_client.upload_blob(blob_name, image_bytes, overwrite=True)
        return blob_client.url

    async def download_blob(
        self, blob_path: str, user_oid: Optional[str] = None
    ) -> Optional[tuple[bytes, BlobProperties]]:
        """Download a blob from Azure Blob Storage."""
        if user_oid is not None:
            raise ValueError(
                "user_oid is not supported for BlobManager. Use AdlsBlobManager for user-specific operations."
            )
        container_client = self.blob_service_client.get_container_client(self.container)
        if not await container_client.exists():
            return None
        if len(blob_path) == 0:
            logger.warning("Blob path is empty")
            return None

        blob_client = container_client.get_blob_client(blob_path)
        try:
            download_response = await blob_client.download_blob()
            if not download_response.properties:
                logger.warning(f"No blob exists for {blob_path}")
                return None

            content = await download_response.readall()

            properties: BlobProperties = {
                "content_settings": {
                    "content_type": (
                        download_response.properties.content_settings.content_type
                        if (
                            hasattr(download_response.properties, "content_settings")
                            and download_response.properties.content_settings
                            and hasattr(download_response.properties.content_settings, "content_type")
                        )
                        else "application/octet-stream"
                    )
                }
            }

            return content, properties
        except ResourceNotFoundError:
            logger.warning("Blob not found: %s", blob_path)
            return None

    async def remove_blob(self, path: Optional[str] = None):
        """Remove blobs from storage."""
        container_client = self.blob_service_client.get_container_client(self.container)
        if not await container_client.exists():
            return
        if path is None:
            prefix = None
            blobs = container_client.list_blob_names()
        else:
            prefix = os.path.splitext(os.path.basename(path))[0]
            blobs = container_client.list_blob_names(name_starts_with=os.path.splitext(os.path.basename(prefix))[0])
        async for blob_path in blobs:
            if (
                prefix is not None
                and (not re.match(rf"{prefix}-\d+\.pdf", blob_path) or not re.match(rf"{prefix}-\d+\.png", blob_path))
            ) or (path is not None and blob_path == os.path.basename(path)):
                continue
            logger.info("Removing blob %s", blob_path)
            await container_client.delete_blob(blob_path)
