import base64
import logging
from typing import Optional, Union

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import ContainerClient
from azure.storage.filedatalake.aio import FileSystemClient
from typing_extensions import Literal, Required, TypedDict


class ImageURL(TypedDict, total=False):
    url: Required[str]
    """Either a URL of the image or the base64 encoded image data."""

    detail: Literal["auto", "low", "high"]
    """Specifies the detail level of the image."""


async def download_blob_as_base64(
    storage_client: Union[ContainerClient, FileSystemClient], blob_url: str, user_oid: Optional[str] = None
) -> Optional[str]:
    """
    Downloads a blob from either Azure Blob Storage or Azure Data Lake Storage and returns it as a base64 encoded string.

    Args:
        storage_client: Either a ContainerClient (for Blob Storage) or FileSystemClient (for Data Lake Storage)
        blob_url: The URL or path to the blob to download
        user_oid: The user's object ID, required for Data Lake Storage operations and access control

    Returns:
        Optional[str]: The base64 encoded image data with data URI scheme prefix, or None if the blob cannot be downloaded
    """
    try:
        # Handle full URLs for both Blob Storage and Data Lake Storage
        if blob_url.startswith("http"):
            url_parts = blob_url.split("/")
            # Skip the domain parts and container/filesystem name to get the blob path
            # For blob: https://{account}.blob.core.windows.net/{container}/{blob_path}
            # For dfs: https://{account}.dfs.core.windows.net/{filesystem}/{path}
            blob_path = "/".join(url_parts[4:])
            # If %20 in URL, replace it with a space
            blob_path = blob_path.replace("%20", " ")
        else:
            # Treat as a direct blob path
            blob_path = blob_url

        # Download the blob using the appropriate client
        if isinstance(storage_client, ContainerClient):
            blob = await storage_client.get_blob_client(blob_path).download_blob()
        else:
            # For Data Lake Storage
            if user_oid is None:
                logging.warning("user_oid must be provided for Data Lake Storage operations.")
                return None

            # Get the directory path and file name from the blob path
            path_parts = blob_path.split("/")
            if len(path_parts) < 2:
                logging.warning(f"Invalid blob path format: {blob_path}")
                return None

            # First verify that the root directory matches the user_oid
            root_dir = path_parts[0]
            if root_dir != user_oid:
                logging.warning(f"User {user_oid} does not have permission to access {blob_path}")
                return None

            # Get the directory client for the full path except the filename
            directory_path = "/".join(path_parts[:-1])
            filename = path_parts[-1]

            try:
                directory_client = storage_client.get_directory_client(directory_path)
                # Verify the directory exists and user has access
                props = await directory_client.get_access_control()
                if not props.get("owner") or props["owner"] != user_oid:
                    logging.warning(f"User {user_oid} does not have access to directory {directory_path}")
                    return None

                # Get and download the file
                file_client = directory_client.get_file_client(filename)
                blob = await file_client.download_file()

            except ResourceNotFoundError:
                logging.warning(f"Directory or file not found: {directory_path}/{filename}")
                return None
            except Exception as e:
                logging.error(f"Error accessing directory {directory_path}: {str(e)}")
                return None

        # Check if the blob has properties, indicating it exists
        if not blob.properties:
            logging.warning(f"No blob exists for {blob_path}")
            return None

        img = base64.b64encode(await blob.readall()).decode("utf-8")
        return f"data:image/png;base64,{img}"
    except ResourceNotFoundError:
        logging.warning(f"No blob exists for {blob_url}")
        return None
    except Exception as e:
        logging.error(f"Error downloading blob {blob_url}: {str(e)}")
        return None
