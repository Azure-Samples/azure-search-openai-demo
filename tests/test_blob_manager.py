import os
import sys
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

import azure.storage.blob.aio
import azure.storage.filedatalake.aio
import pytest

# The pythonpath is configured in pyproject.toml to include app/backend
from prepdocslib.blobmanager import AdlsBlobManager, BlobManager
from prepdocslib.listfilestrategy import File

from .mocks import MockAzureCredential

WINDOWS = sys.platform.startswith("win")


@pytest.fixture
def blob_manager():
    return BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        account=os.environ["AZURE_STORAGE_ACCOUNT"],
        resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    )


@pytest.fixture
def adls_blob_manager(monkeypatch):
    return AdlsBlobManager(
        endpoint="https://test-storage-account.dfs.core.windows.net",
        container="test-storage-container",
        credential=MockAzureCredential(),
    )


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher (due to NamedTemporaryFile)")
@pytest.mark.skipif(WINDOWS, reason="NamedTemporaryFile keeps handles open on Windows")
async def test_upload_and_remove(monkeypatch, mock_env, mock_blob_container_client_exists, blob_manager):
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        f = File(temp_file.file)
        filename = os.path.basename(f.content.name)

        # Set up mock of upload_blob
        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == filename
            return azure.storage.blob.aio.BlobClient.from_blob_url(
                "https://test.blob.core.windows.net/test/test.pdf", credential=MockAzureCredential()
            )

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        await blob_manager.upload_blob(f)
        assert f.url == "https://test.blob.core.windows.net/test/test.pdf"

        # Set up mocks used by remove_blob
        def mock_list_blob_names(*args, **kwargs):
            assert kwargs.get("name_starts_with") == filename.split(".pdf")[0]

            class AsyncBlobItemsIterator:
                def __init__(self, file):
                    self.files = [file, "dontdelete.pdf"]

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.files:
                        return self.files.pop()
                    raise StopAsyncIteration

            return AsyncBlobItemsIterator(filename)

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.list_blob_names", mock_list_blob_names)

        async def mock_delete_blob(self, name, *args, **kwargs):
            assert name == filename
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.delete_blob", mock_delete_blob)

        await blob_manager.remove_blob(f.content.name)


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher (due to NamedTemporaryFile)")
@pytest.mark.skipif(WINDOWS, reason="NamedTemporaryFile keeps handles open on Windows")
async def test_upload_and_remove_all(monkeypatch, mock_env, mock_blob_container_client_exists, blob_manager):
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        f = File(temp_file.file)
        filename = os.path.basename(f.content.name)

        # Set up mock of upload_blob
        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == filename
            return azure.storage.blob.aio.BlobClient.from_blob_url(
                "https://test.blob.core.windows.net/test/test.pdf", credential=MockAzureCredential()
            )

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        await blob_manager.upload_blob(f)
        assert f.url == "https://test.blob.core.windows.net/test/test.pdf"

        # Set up mocks used by remove_blob
        def mock_list_blob_names(*args, **kwargs):
            assert kwargs.get("name_starts_with") is None

            class AsyncBlobItemsIterator:
                def __init__(self, file):
                    self.files = [file]

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.files:
                        return self.files.pop()
                    raise StopAsyncIteration

            return AsyncBlobItemsIterator(filename)

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.list_blob_names", mock_list_blob_names)

        async def mock_delete_blob(self, name, *args, **kwargs):
            assert name == filename
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.delete_blob", mock_delete_blob)

        await blob_manager.remove_blob()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher (due to NamedTemporaryFile)")
@pytest.mark.skipif(WINDOWS, reason="NamedTemporaryFile keeps handles open on Windows")
async def test_create_container_upon_upload(monkeypatch, mock_env, blob_manager):
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        f = File(temp_file.file)
        filename = os.path.basename(f.content.name)

        # Set up mocks used by upload_blob
        async def mock_exists(*args, **kwargs):
            return False

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

        async def mock_create_container(*args, **kwargs):
            return

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.create_container", mock_create_container)

        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == filename
            return azure.storage.blob.aio.BlobClient.from_blob_url(
                "https://test.blob.core.windows.net/test/test.pdf", credential=MockAzureCredential()
            )

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        await blob_manager.upload_blob(f)
        assert f.url == "https://test.blob.core.windows.net/test/test.pdf"


@pytest.mark.asyncio
async def test_dont_remove_if_no_container(
    monkeypatch, mock_env, mock_blob_container_client_does_not_exist, blob_manager
):
    async def mock_delete_blob(*args, **kwargs):
        assert False, "delete_blob() shouldn't have been called"  # pragma: no cover

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.delete_blob", mock_delete_blob)

    await blob_manager.remove_blob()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher (due to NamedTemporaryFile)")
@pytest.mark.skipif(WINDOWS, reason="NamedTemporaryFile keeps handles open on Windows")
@pytest.mark.parametrize("directory_exists", [True, False])
async def test_upload_document_image(monkeypatch, mock_env, directory_exists):
    # Create a blob manager with an image container
    blob_manager = BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        account=os.environ["AZURE_STORAGE_ACCOUNT"],
        resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        image_container="test-image-container",
    )

    # Create a test file and image bytes
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        document_file = File(temp_file.file)
        # Create a simple 1x1 transparent PNG image
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xa3\xb8\xfb\x26\x00\x00\x00\x00IEND\xaeB`\x82"
        image_filename = "test_image.png"
        image_page_num = 0

        # No need to mock PIL - it will process the tiny PNG image
        # PIL operations will be simple and fast with this small image

        # Mock container client operations
        async def mock_exists(*args, **kwargs):
            return directory_exists

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

        async def mock_create_container(*args, **kwargs):
            return

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.create_container", mock_create_container)

        expected_blob_name = f"{os.path.basename(temp_file.name)}/page{image_page_num}/{image_filename}"

        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == expected_blob_name
            return azure.storage.blob.aio.BlobClient.from_blob_url(
                "https://test.blob.core.windows.net/test-image-container/test-image-url",
                credential=MockAzureCredential(),
            )

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        # Call the method and verify the results
        document_filename = document_file.filename()
        result_url = await blob_manager.upload_document_image(
            document_filename, image_bytes, image_filename, image_page_num
        )

        assert result_url == "https://test.blob.core.windows.net/test-image-container/test-image-url"


@pytest.mark.asyncio
async def test_adls_upload_document_image(monkeypatch, mock_env, adls_blob_manager):

    # Test parameters
    document_filename = "test_document.pdf"
    image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xa3\xb8\xfb\x26\x00\x00\x00\x00IEND\xaeB`\x82"
    image_filename = "test_image.png"
    image_page_num = 0
    user_oid = "test-user-123"

    # Mock directory path operations
    image_directory_path = f"{user_oid}/images/{document_filename}/page_{image_page_num}"

    # Mock the _ensure_directory method to avoid needing Azure Data Lake Storage
    mock_directory_client = MagicMock()
    mock_file_client = MagicMock()
    mock_directory_client.get_file_client.return_value = mock_file_client
    mock_file_client.url = f"https://test-storage-account.dfs.core.windows.net/{image_directory_path}/{image_filename}"

    async def mock_ensure_directory(self, directory_path, user_oid):
        assert directory_path in [user_oid, image_directory_path]
        return mock_directory_client

    monkeypatch.setattr(AdlsBlobManager, "_ensure_directory", mock_ensure_directory)

    # Mock file_client.upload_data to avoid actual upload
    async def mock_upload_data(data, overwrite=True, metadata=None):
        assert overwrite is True
        assert metadata == {"UploadedBy": user_oid}
        # Verify we're adding the citation to the image
        assert len(data) > len(image_bytes)  # The citation adds to the size

    mock_file_client.upload_data = mock_upload_data

    # Call the method and verify the results
    result_url = await adls_blob_manager.upload_document_image(
        document_filename, image_bytes, image_filename, image_page_num, user_oid
    )

    # Verify the URL is correct and unquoted
    assert result_url == f"https://test-storage-account.dfs.core.windows.net/{image_directory_path}/{image_filename}"
    assert result_url == f"https://test-storage-account.dfs.core.windows.net/{image_directory_path}/{image_filename}"

    # Test with missing user_oid
    with pytest.raises(ValueError, match="user_oid must be provided for user-specific operations."):
        await adls_blob_manager.upload_document_image(document_filename, image_bytes, image_filename, image_page_num)


def test_get_managed_identity_connection_string(mock_env, blob_manager):
    assert (
        blob_manager.get_managedidentity_connectionstring()
        == "ResourceId=/subscriptions/test-storage-subid/resourceGroups/test-storage-rg/providers/Microsoft.Storage/storageAccounts/test-storage-account;"
    )


def test_sourcepage_from_file_page():
    assert BlobManager.sourcepage_from_file_page("test.pdf", 0) == "test.pdf#page=1"
    assert BlobManager.sourcepage_from_file_page("test.html", 0) == "test.html"


def test_blob_name_from_file_name():
    assert BlobManager.blob_name_from_file_name("tmp/test.pdf") == "test.pdf"
    assert BlobManager.blob_name_from_file_name("tmp/test.html") == "test.html"


@pytest.mark.asyncio
async def test_download_blob(monkeypatch, mock_env, mock_blob_container_client_exists, blob_manager):
    # Mock the download_blob method
    test_content = b"test content bytes"

    class MockDownloadResponse:
        def __init__(self):
            # Create properties with content_settings
            class ContentSettings:
                content_type = "application/pdf"

            class Properties:
                def __init__(self):
                    self.content_settings = ContentSettings()

            self.properties = Properties()

        async def readall(self):
            return test_content

    async def mock_download_blob(*args, **kwargs):
        return MockDownloadResponse()

    monkeypatch.setattr("azure.storage.blob.aio.BlobClient.download_blob", mock_download_blob)

    result = await blob_manager.download_blob("test_document.pdf")

    assert result is not None
    content, properties = result
    assert content == test_content
    assert properties["content_settings"]["content_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_blob_not_found(monkeypatch, mock_env, mock_blob_container_client_exists, blob_manager):
    # Mock the download_blob method to raise ResourceNotFoundError
    async def mock_download_blob(*args, **kwargs):
        from azure.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Blob not found")

    monkeypatch.setattr("azure.storage.blob.aio.BlobClient.download_blob", mock_download_blob)

    result = await blob_manager.download_blob("nonexistent.pdf")

    assert result is None


@pytest.mark.asyncio
async def test_download_blob_container_not_exist(
    monkeypatch, mock_env, mock_blob_container_client_does_not_exist, blob_manager
):
    result = await blob_manager.download_blob("test_document.pdf")

    assert result is None


@pytest.mark.asyncio
async def test_download_blob_empty_path(monkeypatch, mock_env, mock_blob_container_client_exists, blob_manager):
    result = await blob_manager.download_blob("")

    assert result is None


@pytest.mark.asyncio
async def test_download_blob_with_user_oid(monkeypatch, mock_env, blob_manager):
    with pytest.raises(ValueError) as excinfo:
        await blob_manager.download_blob("test_document.pdf", user_oid="user123")

    assert "user_oid is not supported for BlobManager" in str(excinfo.value)


@pytest.mark.asyncio
async def test_download_blob_properties_none(monkeypatch, mock_env, mock_blob_container_client_exists, blob_manager):
    """Test that BlobManager.download_blob returns None when download_response.properties is None."""

    # Mock the download_blob method with properties=None
    class MockDownloadResponseWithNoProperties:
        def __init__(self):
            self.properties = None  # This is the condition we're testing

        async def readall(self):
            assert False, "This should not be called, as properties is None"  # pragma: no cover

    async def mock_download_blob(*args, **kwargs):
        return MockDownloadResponseWithNoProperties()

    monkeypatch.setattr("azure.storage.blob.aio.BlobClient.download_blob", mock_download_blob)

    # Call the download_blob method
    result = await blob_manager.download_blob("test_document.pdf")

    # Verify the result is None due to properties being None
    assert result is None


@pytest.mark.asyncio
async def test_adls_download_blob_permission_denied(monkeypatch, mock_env, adls_blob_manager):
    """Test that AdlsBlobManager.download_blob returns None when a user tries to access a blob that doesn't belong to them."""
    user_oid = "test-user-123"
    other_user_oid = "another-user-456"
    blob_path = f"{other_user_oid}/document.pdf"  # Path belonging to another user

    # Attempt to download blob
    result = await adls_blob_manager.download_blob(blob_path, user_oid)

    # Verify the blob access is denied and the method returns None
    assert result is None

    # Also test the case where no user_oid is provided
    result = await adls_blob_manager.download_blob(blob_path, None)
    assert result is None


@pytest.mark.asyncio
async def test_adls_download_blob_with_permission(
    monkeypatch, mock_data_lake_service_client, mock_user_directory_client, adls_blob_manager
):
    """Test that AdlsBlobManager.download_blob works when a user has permission to access a blob."""

    content, properties = await adls_blob_manager.download_blob("OID_X/document.pdf", "OID_X")

    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert properties["content_settings"]["content_type"] == "application/octet-stream"
