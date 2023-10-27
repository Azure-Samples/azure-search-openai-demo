import os
import sys
from tempfile import NamedTemporaryFile

import pytest
from conftest import MockAzureCredential

from scripts.prepdocslib.blobmanager import BlobManager
from scripts.prepdocslib.listfilestrategy import File


@pytest.fixture
def blob_manager(monkeypatch):
    return BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        verbose=True,
    )


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info.minor < 10, reason="requires Python 3.10 or higher")
async def test_upload_and_remove(monkeypatch, mock_env, blob_manager):
    with NamedTemporaryFile(suffix=".pdf") as temp_file:
        f = File(temp_file.file)
        filename = f.content.name.split("/tmp/")[1]

        # Set up mocks used by upload_blob
        async def mock_exists(*args, **kwargs):
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == filename
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        await blob_manager.upload_blob(f)

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
        print(f.content.name)
        filename = f.content.name.split("/tmp/")[1]

        # Set up mocks used by upload_blob
        async def mock_exists(*args, **kwargs):
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == filename
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        await blob_manager.upload_blob(f)

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
        filename = f.content.name.split("/tmp/")[1]

        # Set up mocks used by upload_blob
        async def mock_exists(*args, **kwargs):
            return False

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

        async def mock_create_container(*args, **kwargs):
            return

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.create_container", mock_create_container)

        async def mock_upload_blob(self, name, *args, **kwargs):
            assert name == filename
            return True

        monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

        await blob_manager.upload_blob(f)


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


def test_sourcepage_from_file_page():
    assert BlobManager.sourcepage_from_file_page("test.pdf", 0) == "test.pdf#page=1"
    assert BlobManager.sourcepage_from_file_page("test.html", 0) == "test.html"


def test_blob_name_from_file_name():
    assert BlobManager.blob_name_from_file_name("tmp/test.pdf") == "test.pdf"
    assert BlobManager.blob_name_from_file_name("tmp/test.html") == "test.html"
