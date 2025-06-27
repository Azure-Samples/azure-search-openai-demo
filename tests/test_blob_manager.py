import os
import sys
from tempfile import NamedTemporaryFile

import azure.storage.blob.aio
import pytest

from prepdocslib.blobmanager import BlobManager
from prepdocslib.listfilestrategy import File

from .mocks import MockAzureCredential


@pytest.fixture
def blob_manager(monkeypatch):
    return BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        account=os.environ["AZURE_STORAGE_ACCOUNT"],
        resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
    )


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher")
async def test_upload_and_remove(monkeypatch, mock_env, blob_manager):
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        f = File(temp_file.file)
        filename = os.path.basename(f.content.name)

        # Set up mocks used by upload_blob
        async def mock_exists(*args, **kwargs):
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

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
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher")
async def test_upload_and_remove_all(monkeypatch, mock_env, blob_manager):
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        f = File(temp_file.file)
        filename = os.path.basename(f.content.name)

        # Set up mocks used by upload_blob
        async def mock_exists(*args, **kwargs):
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

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
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher")
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
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher")
async def test_dont_remove_if_no_container(monkeypatch, mock_env, blob_manager):
    async def mock_exists(*args, **kwargs):
        return False

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

    async def mock_delete_blob(*args, **kwargs):
        assert False, "delete_blob() shouldn't have been called"

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.delete_blob", mock_delete_blob)

    await blob_manager.remove_blob()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher")
async def test_upload_document_image(monkeypatch, mock_env):
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
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

        expected_blob_name = f"{os.path.basename(temp_file.name)}/page{image_page_num}/{image_filename}"

        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == expected_blob_name
            return azure.storage.blob.aio.BlobClient.from_blob_url(
                "https://test.blob.core.windows.net/test-image-container/test-image-url",
                credential=MockAzureCredential(),
            )

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        # Call the method and verify the results
        result_url = await blob_manager.upload_document_image(
            document_file, image_bytes, image_filename, image_page_num
        )

        assert result_url == "https://test.blob.core.windows.net/test-image-container/test-image-url"


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
