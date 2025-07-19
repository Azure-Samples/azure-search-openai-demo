import os

import pytest
from azure.search.documents.aio import SearchClient

from prepdocslib.blobmanager import BlobManager
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy
from prepdocslib.listfilestrategy import (
    ADLSGen2ListFileStrategy,
)
from prepdocslib.strategy import SearchInfo
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SimpleTextSplitter

from .mocks import MockAzureCredential


@pytest.mark.asyncio
async def test_file_strategy_adls2(monkeypatch, mock_env, mock_data_lake_service_client):
    adlsgen2_list_strategy = ADLSGen2ListFileStrategy(
        data_lake_storage_account="a", data_lake_filesystem="a", data_lake_path="a", credential=MockAzureCredential()
    )
    blob_manager = BlobManager(
        endpoint=f"https://{os.environ['AZURE_STORAGE_ACCOUNT']}.blob.core.windows.net",
        credential=MockAzureCredential(),
        container=os.environ["AZURE_STORAGE_CONTAINER"],
        account=os.environ["AZURE_STORAGE_ACCOUNT"],
        resourceGroup=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscriptionId=os.environ["AZURE_SUBSCRIPTION_ID"],
        store_page_images=False,
    )

    # Set up mocks used by upload_blob
    async def mock_exists(*args, **kwargs):
        return True

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.exists", mock_exists)

    uploaded_to_blob = []

    async def mock_upload_blob(self, name, *args, **kwargs):
        uploaded_to_blob.append(name)

    monkeypatch.setattr("azure.storage.blob.aio.ContainerClient.upload_blob", mock_upload_blob)

    search_info = SearchInfo(
        endpoint="https://testsearchclient.blob.core.windows.net",
        credential=MockAzureCredential(),
        index_name="test",
    )

    uploaded_to_search = []

    async def mock_upload_documents(self, documents):
        uploaded_to_search.extend(documents)

    monkeypatch.setattr(SearchClient, "upload_documents", mock_upload_documents)

    file_strategy = FileStrategy(
        list_file_strategy=adlsgen2_list_strategy,
        blob_manager=blob_manager,
        search_info=search_info,
        file_processors={".txt": FileProcessor(TextParser(), SimpleTextSplitter())},
        use_acls=True,
    )

    await file_strategy.run()

    assert len(uploaded_to_blob) == 0
    assert len(uploaded_to_search) == 3
    assert uploaded_to_search == [
        {
            "id": "file-a_txt-612E7478747B276F696473273A205B27412D555345522D4944275D2C202767726F757073273A205B27412D47524F55502D4944275D7D-page-0",
            "content": "texttext",
            "category": None,
            "groups": ["A-GROUP-ID"],
            "oids": ["A-USER-ID"],
            "sourcepage": "a.txt",
            "sourcefile": "a.txt",
            "storageUrl": "https://test.blob.core.windows.net/a.txt",
        },
        {
            "id": "file-b_txt-622E7478747B276F696473273A205B27422D555345522D4944275D2C202767726F757073273A205B27422D47524F55502D4944275D7D-page-0",
            "content": "texttext",
            "category": None,
            "groups": ["B-GROUP-ID"],
            "oids": ["B-USER-ID"],
            "sourcepage": "b.txt",
            "sourcefile": "b.txt",
            "storageUrl": "https://test.blob.core.windows.net/b.txt",
        },
        {
            "id": "file-c_txt-632E7478747B276F696473273A205B27432D555345522D4944275D2C202767726F757073273A205B27432D47524F55502D4944275D7D-page-0",
            "content": "texttext",
            "category": None,
            "groups": ["C-GROUP-ID"],
            "oids": ["C-USER-ID"],
            "sourcepage": "c.txt",
            "sourcefile": "c.txt",
            "storageUrl": "https://test.blob.core.windows.net/c.txt",
        },
    ]
