import base64
import logging
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import ContainerClient
from typing_extensions import Literal, Required, TypedDict


class ImageURL(TypedDict, total=False):
    url: Required[str]
    """Either a URL of the image or the base64 encoded image data."""

    detail: Literal["auto", "low", "high"]
    """Specifies the detail level of the image."""


async def download_blob_as_base64(blob_container_client: ContainerClient, blob_url: str) -> Optional[str]:
    try:
        # Handle full URLs
        if blob_url.startswith("http"):
            # Extract blob path from full URL
            # URL format: https://{account}.blob.core.windows.net/{container}/{blob_path}
            url_parts = blob_url.split("/")
            # Skip the domain parts and container name to get the blob path
            blob_path = "/".join(url_parts[4:])
            # If %20 in URL, replace it with a space
            blob_path = blob_path.replace("%20", " ")
        else:
            # Treat as a direct blob path
            blob_path = blob_url

        # Download the blob
        blob = await blob_container_client.get_blob_client(blob_path).download_blob()
        if not blob.properties:
            logging.warning(f"No blob exists for {blob_path}")
            return None

        img = base64.b64encode(await blob.readall()).decode("utf-8")
        return f"data:image/png;base64,{img}"
    except ResourceNotFoundError:
        logging.warning(f"No blob exists for {blob_path}")
        return None
    except Exception as e:
        logging.error(f"Error downloading blob {blob_url}: {str(e)}")
        return None
