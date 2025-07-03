import io
import logging
import os
import re
from pathlib import Path
from typing import IO, Optional, Union
from urllib.parse import unquote

from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.filedatalake.aio import FileSystemClient
from PIL import Image, ImageDraw, ImageFont

from .listfilestrategy import File

logger = logging.getLogger("scripts")


class BaseBlobManager:
    """
    Base class for Azure Storage operations, providing common file naming and path utilities
    """

    @classmethod
    def sourcepage_from_file_page(cls, filename, page=0) -> str:
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return f"{os.path.basename(filename)}#page={page+1}"
        else:
            return os.path.basename(filename)

    @classmethod
    def blob_image_name_from_file_page(cls, filename, page=0) -> str:
        return os.path.splitext(os.path.basename(filename))[0] + f"-{page+1}" + ".png"

    @classmethod
    def blob_name_from_file_name(cls, filename) -> str:
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
            A tuple containing (BytesIO of the modified image, format of the image)
        """
        # Load and modify the image to add text
        image = Image.open(io.BytesIO(image_bytes))
        line_height = 30
        text_height = line_height * 2  # Two lines of text
        new_img = Image.new("RGB", (image.width, image.height + text_height), "white")
        new_img.paste(image, (0, text_height))

        # Add text
        draw = ImageDraw.Draw(new_img)
        sourcepage = cls.sourcepage_from_file_page(document_filename, page=page_num)
        text = sourcepage
        figure_text = image_filename

        # Load the Jupiteroid font which is included in the repo
        font_path = Path(__file__).parent / "Jupiteroid-Regular.ttf"
        font = ImageFont.truetype(str(font_path), 20)  # Slightly smaller font for better fit

        # Calculate text widths for right alignment
        fig_width = draw.textlength(figure_text, font=font)

        # Left align document name, right align figure name
        padding = 20  # Padding from edges
        draw.text((padding, 5), text, font=font, fill="black")  # Left aligned
        draw.text(
            (new_img.width - fig_width - padding, line_height + 5), figure_text, font=font, fill="black"
        )  # Right aligned

        # Convert back to bytes
        output = io.BytesIO()
        format = image.format or "PNG"
        new_img.save(output, format=format)

        return output.getvalue()


class AdlsBlobManager(BaseBlobManager):
    """
    Manager for Azure Data Lake Storage blob operations, particularly for user-specific file operations.
    Documents are stored directly in the user's directory for backwards compatibility.
    Images are stored in a separate images subdirectory for better organization.
    """

    def __init__(self, filesystem_client: FileSystemClient):
        self.filesystem_client = filesystem_client

    async def _ensure_directory(self, directory_path: str, owner: str = None) -> None:
        """
        Ensures that a directory path exists and has proper permissions.
        Creates the entire path in a single operation if it doesn't exist.

        Args:
            directory_path: Full path of directory to create (e.g., 'user123/images/mydoc')
            owner: The owner to set for all created directories
        """
        directory_client = self.filesystem_client.get_directory_client(directory_path)
        try:
            await directory_client.get_directory_properties()
        except ResourceNotFoundError:
            logger.info("Creating directory path %s", directory_path)
            await directory_client.create_directory()
            if owner:
                await directory_client.set_access_control(owner=owner)

    async def upload_blob(self, file: Union[File, IO], filename: str, user_oid: str) -> str:
        """
        Uploads a file directly to the user's directory in ADLS (no subdirectory).

        Args:
            file: Either a File object or an IO object to upload
            filename: The name of the file to upload
            user_oid: The user's object ID

        Returns:
            str: The URL of the uploaded file, with forward slashes (not URL-encoded)
        """
        # Ensure user directory exists but don't create a subdirectory
        await self._ensure_directory(user_oid, owner=user_oid)

        # Create file directly in user directory
        file_client = self.filesystem_client.get_file_client(f"{user_oid}/{filename}")

        # Handle both File and IO objects
        if isinstance(file, File):
            file_io = file.content
        else:
            file_io = file

        # Ensure the file is at the beginning
        file_io.seek(0)

        await file_client.upload_data(file_io, overwrite=True)

        # Reset the file position for any subsequent reads
        file_io.seek(0)

        # Decode the URL to convert %2F back to / and other escaped characters
        return unquote(file_client.url)

    def _get_image_directory_path(self, document_filename: str, user_oid: str, page_num: Optional[int] = None) -> str:
        """
        Returns the standardized path for storing document images.

        Args:
            document_filename: The name of the document
            user_oid: The user's object ID
            page_num: Optional page number. If provided, includes a page-specific subdirectory

        Returns:
            str: Full path to the image directory
        """
        if page_num is not None:
            return f"{user_oid}/images/{document_filename}/page_{page_num}"
        return f"{user_oid}/images/{document_filename}"

    async def upload_document_image(
        self,
        document_filename: str,
        image_bytes: bytes,
        image_filename: str,
        image_page_num: int,
        user_oid: str,
    ) -> Optional[str]:
        """
        Uploads an image from a document to ADLS in a directory structure:
        {user_oid}/{document_name}/images/{image_name}
        This structure allows for easy cleanup when documents are deleted.

        Args:
            document_filename: The name of the document containing the image
            image_bytes: The image data to upload
            image_filename: The name to give the image file
            image_page_num: The page number where the image appears in the document
            user_oid: The user's object ID

        Returns:
            str: The URL of the uploaded file, with forward slashes (not URL-encoded)
        """
        directory_path = self._get_image_directory_path(document_filename, user_oid, image_page_num)
        await self._ensure_directory(directory_path, owner=user_oid)
        file_client = self.filesystem_client.get_file_client(f"{directory_path}/{image_filename}")
        image_bytes = BaseBlobManager.add_image_citation(image_bytes, document_filename, image_filename, image_page_num)
        logger.info("Uploading document image '%s' to '%s'", image_filename, directory_path)
        await file_client.upload_data(image_bytes, overwrite=True, metadata={"UploadedBy": user_oid})
        return unquote(file_client.url)

    async def remove_blob(self, filename: str, user_oid: str) -> None:
        """
        Deletes a file from the user's directory in ADLS and any associated image directories.
        The following will be deleted:
        - {user_oid}/{filename}
        - {user_oid}/images/{filename}/* (recursively)

        Args:
            filename: The name of the file to delete
            user_oid: The user's object ID

        Raises:
            ResourceNotFoundError: If the file does not exist
        """
        logger.info(f"Deleting file '{filename}' and associated images for user '{user_oid}'")

        # Delete the main document file
        user_directory_client = self.filesystem_client.get_directory_client(user_oid)
        file_client = user_directory_client.get_file_client(filename)
        await file_client.delete_file()

        # Try to delete any associated image directories
        try:
            image_directory_path = self._get_image_directory_path(filename, user_oid)
            image_directory_client = self.filesystem_client.get_directory_client(image_directory_path)
            await image_directory_client.delete_directory()
            logger.info(f"Deleted associated image directory: {image_directory_path}")
        except ResourceNotFoundError:
            # It's okay if there was no image directory
            logger.debug(f"No image directory found at {image_directory_path}")
            pass

    async def list_blobs(self, user_oid: str) -> list[str]:
        """
        Lists the uploaded documents for the given user.
        Only returns files directly in the user's directory, not in subdirectories.
        Excludes image files and the images directory.

        Args:
            user_oid: The user's object ID

        Returns:
            list[str]: List of filenames that belong to the user
        """
        files = []
        try:
            all_paths = self.filesystem_client.get_paths(path=user_oid)
            async for path in all_paths:
                # Split path into parts (user_oid/filename or user_oid/directory/files)
                path_parts = path.name.split("/", 1)
                if len(path_parts) != 2:
                    continue

                filename = path_parts[1]
                # Only include files that are:
                # 1. Directly in the user's directory (no additional slashes)
                # 2. Not image files
                # 3. Not in a directory containing 'images'
                if (
                    "/" not in filename
                    and not any(filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"])
                    and "images" not in filename
                ):
                    files.append(filename)
        except ResourceNotFoundError as error:
            if error.status_code != 404:
                logger.exception("Error listing uploaded files", error)
            # Return empty list for 404 (no directory) as this is expected for new users
        return files


class BlobManager(BaseBlobManager):
    """
    Class to manage uploading and deleting blobs containing citation information from a blob storage account
    """

    def __init__(
        self,
        endpoint: str,
        container: str,
        account: str,
        credential: Union[AsyncTokenCredential, str],
        resource_group: str,
        subscription_id: str,
        image_container: Optional[str] = None,  # Added this parameter
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.account = account
        self.container = container
        self.resource_group = resource_group
        self.subscription_id = subscription_id
        self.image_container = image_container

    async def upload_blob(self, file: File) -> Optional[list[str]]:
        async with BlobServiceClient(
            account_url=self.endpoint, credential=self.credential, max_single_put_size=4 * 1024 * 1024
        ) as service_client, service_client.get_container_client(self.container) as container_client:
            if not await container_client.exists():
                await container_client.create_container()

            # Re-open and upload the original file
            if file.url is None:
                with open(file.content.name, "rb") as reopened_file:
                    blob_name = self.blob_name_from_file_name(file.content.name)
                    logger.info("Uploading blob for document '%s'", blob_name)
                    blob_client = await container_client.upload_blob(blob_name, reopened_file, overwrite=True)
                    file.url = blob_client.url
        return None

    async def upload_document_image(
        self, document_filename: str, image_bytes: bytes, image_filename: str, image_page_num: int
    ) -> Optional[str]:
        if self.image_container is None:
            raise ValueError(
                "Image container name is not set. Re-run `azd provision` to automatically set up the images container."
            )
        async with BlobServiceClient(
            account_url=self.endpoint, credential=self.credential, max_single_put_size=4 * 1024 * 1024
        ) as service_client, service_client.get_container_client(self.image_container) as container_client:
            if not await container_client.exists():
                await container_client.create_container()
            image_bytes = self.add_image_citation(image_bytes, document_filename, image_filename, image_page_num)
            blob_name = f"{self.blob_name_from_file_name(document_filename)}/page{image_page_num}/{image_filename}"
            logger.info("Uploading blob for document image '%s'", blob_name)
            blob_client = await container_client.upload_blob(blob_name, image_bytes, overwrite=True)
            return blob_client.url
        return None

    def get_managedidentity_connectionstring(self):
        return f"ResourceId=/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.Storage/storageAccounts/{self.account};"

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
                if (
                    prefix is not None
                    and (
                        not re.match(rf"{prefix}-\d+\.pdf", blob_path) or not re.match(rf"{prefix}-\d+\.png", blob_path)
                    )
                ) or (path is not None and blob_path == os.path.basename(path)):
                    continue
                logger.info("Removing blob %s", blob_path)
                await container_client.delete_blob(blob_path)
