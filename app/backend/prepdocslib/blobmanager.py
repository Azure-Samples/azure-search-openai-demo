import io
import logging
import os
import re
from pathlib import Path
from typing import IO, Optional, Union

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
        text_height = 40
        new_img = Image.new("RGB", (image.width, image.height + text_height), "white")
        new_img.paste(image, (0, text_height))

        # Add text
        draw = ImageDraw.Draw(new_img)
        sourcepage = cls.sourcepage_from_file_page(document_filename, page=page_num)

        text = f"Document:  {sourcepage}"

        font = None
        try:
            font_path = Path(__file__).parent / "Jupiteroid-Regular.ttf"
            font = ImageFont.truetype(str(font_path), 24)
        except OSError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 24)
            except OSError:
                logger.info("Unable to find arial.ttf or FreeMono.ttf, using default font")

        # Draw document text on left
        draw.text((10, 10), text, font=font, fill="black")

        # Draw figure text on right
        figure_text = f"Figure:  {image_filename}"
        if font:
            # Get the width of the text to position it on the right
            text_width = draw.textlength(figure_text, font=font)
            draw.text((new_img.width - text_width - 10, 10), figure_text, font=font, fill="black")
        else:
            # If no font available, make a best effort to position on right
            draw.text((new_img.width - 200, 10), figure_text, font=font, fill="black")

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

    async def _ensure_directory(self, path_components: list[str], owner: str = None) -> str:
        """
        Ensures that a directory path exists and has proper permissions.
        Creates the entire path in a single operation if it doesn't exist.

        Args:
            path_components: List of directory names to create (e.g., ['user123', 'mydoc', 'images'])
            owner: The owner to set for all created directories

        Returns:
            str: The full path that was created
        """
        # Filter out empty components and join with /
        full_path = "/".join(component for component in path_components if component)
        if not full_path:
            raise ValueError("No valid path components provided")

        directory_client = self.filesystem_client.get_directory_client(full_path)
        try:
            await directory_client.get_directory_properties()
        except ResourceNotFoundError:
            logger.info("Creating directory path %s", full_path)
            await directory_client.create_directory()
            if owner:
                await directory_client.set_access_control(owner=owner)

        return full_path

    async def upload_blob(self, file: Union[File, IO], filename: str, user_oid: str) -> str:
        """
        Uploads a file directly to the user's directory in ADLS (no subdirectory).

        Args:
            file: Either a File object or an IO object to upload
            filename: The name of the file to upload
            user_oid: The user's object ID

        Returns:
            str: The URL of the uploaded file
        """
        # Ensure user directory exists but don't create a subdirectory
        await self._ensure_directory([user_oid], owner=user_oid)

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

        return file_client.url

    async def upload_document_image(
        self, document_filename: str, image_bytes: bytes, image_filename: str, image_page_num: int, user_oid: str
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
            str: The URL of the uploaded image file
        """
        directory_path = await self._ensure_directory(
            [user_oid, "images", document_filename, f"page_{image_page_num}"], owner=user_oid
        )
        file_client = self.filesystem_client.get_file_client(f"{directory_path}/{image_filename}")
        image_bytes = BaseBlobManager.add_image_citation(image_bytes, document_filename, image_filename, image_page_num)
        logger.info("Uploading document image '%s' to '%s'", image_filename, directory_path)
        await file_client.upload_data(image_bytes, overwrite=True, metadata={"UploadedBy": user_oid})
        return file_client.url


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
