import io
import logging
import os
import re
from pathlib import Path
from typing import Optional, Union

from azure.core.credentials_async import AsyncTokenCredential
from azure.storage.blob.aio import BlobServiceClient
from PIL import Image, ImageDraw, ImageFont

from .listfilestrategy import File

logger = logging.getLogger("scripts")


class BlobManager:
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
                    blob_name = BlobManager.blob_name_from_file_name(file.content.name)
                    logger.info("Uploading blob for document %s", blob_name)
                    blob_client = await container_client.upload_blob(blob_name, reopened_file, overwrite=True)
                    file.url = blob_client.url
        return None

    async def upload_document_image(
        self, document_file: File, image_bytes: bytes, image_filename: str, image_page_num: int
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

            # Load and modify the image to add text
            image = Image.open(io.BytesIO(image_bytes))
            text_height = 40
            new_img = Image.new("RGB", (image.width, image.height + text_height), "white")
            new_img.paste(image, (0, text_height))

            # Add text
            draw = ImageDraw.Draw(new_img)
            sourcepage = BlobManager.sourcepage_from_file_page(document_file.content.name, page=image_page_num)
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
            new_img.save(output, format=image.format or "PNG")
            output.seek(0)

            blob_name = (
                f"{self.blob_name_from_file_name(document_file.content.name)}/page{image_page_num}/{image_filename}"
            )
            logger.info("Uploading blob for document image %s", blob_name)
            blob_client = await container_client.upload_blob(blob_name, output, overwrite=True)
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
