import builtins
import json

import aiohttp
import azure.storage.filedatalake.aio
import pytest

from .mocks import MockAzureCredential, MockResponse
from scripts.adlsgen2setup import AdlsGen2Setup

valid_data_access_control_format = {
    "files": {
        "a.txt": {"directory": "d1"},
        "b.txt": {"directory": "d2"},
        "c.txt": {"directory": "d1"},
    },
    "directories": {
        "d1": {"groups": ["GROUP_A"]},
        "d2": {"groups": ["GROUP_A", "GROUP_B"]},
        "/": {"groups": ["GROUP_C"]},
    },
    "groups": ["GROUP_A", "GROUP_B", "GROUP_C"],
}


@pytest.fixture
def mock_open(monkeypatch):
    class MockOpenedFile:
        def __enter__(self, *args, **kwargs):
            pass

        def __exit__(self, *args, **kwargs):
            return self

    def mock_open(*args, **kwargs):
        return MockOpenedFile()

    monkeypatch.setattr(builtins, "open", mock_open)


@pytest.fixture
def mock_adlsgen2setup(monkeypatch):
    def mock_adlsgen2setup_create_service_client(self, *args, **kwargs):
        try:
            return self.service_client
        except AttributeError:
            self.service_client = azure.storage.filedatalake.aio.DataLakeServiceClient()
            return self.service_client

    monkeypatch.setattr(AdlsGen2Setup, "create_service_client", mock_adlsgen2setup_create_service_client)


@pytest.fixture
def mock_get_group_success(monkeypatch):
    def mock_get(self, url, *args, **kwargs):
        group_id = None
        if "GROUP_A" in url:
            group_id = "GROUP_A_ID"
        elif "GROUP_B" in url:
            group_id = "GROUP_B_ID"
        elif "GROUP_C" in url:
            group_id = "GROUP_C_ID"
        else:
            pytest.fail("Unknown group")
        return MockResponse(
            text=json.dumps({"value": [{"id": group_id}]}),
            status=200,
        )

    monkeypatch.setattr(aiohttp.ClientSession, "get", mock_get)


@pytest.fixture
def mock_get_group_missing(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            text=json.dumps({"value": []}),
            status=200,
        )

    monkeypatch.setattr(aiohttp.ClientSession, "get", mock_get)


@pytest.fixture
def mock_put_group(monkeypatch):
    def mock_post(*args, **kwargs):
        obj = kwargs.get("json")
        assert obj
        assert "displayName" in obj
        assert obj.get("groupTypes") == ["Unified"]
        assert obj.get("securityEnabled") is False
        return MockResponse(
            text=json.dumps({"id": obj["displayName"] + "_ID_CREATED"}),
            status=201,
        )

    monkeypatch.setattr(aiohttp.ClientSession, "post", mock_post)


@pytest.mark.asyncio
async def test_adls_gen2_setup(
    monkeypatch, mock_data_lake_service_client, mock_adlsgen2setup, mock_get_group_success, mock_open
):
    command = AdlsGen2Setup(
        data_directory="",
        storage_account_name="STORAGE",
        filesystem_name="FILESYSTEM",
        security_enabled_groups=False,
        data_access_control_format=valid_data_access_control_format,
        credentials=MockAzureCredential(),
    )
    await command.run()

    assert command.service_client
    assert len(command.service_client.filesystems) == 1
    assert "FILESYSTEM" in command.service_client.filesystems
    filesystem_client = command.service_client.filesystems["FILESYSTEM"]
    assert len(filesystem_client.directories) == 3
    assert "/" in filesystem_client.directories
    assert "d1" in filesystem_client.directories
    assert "d2" in filesystem_client.directories
    assert len(filesystem_client.directories["d1"].files) == 2
    assert "a.txt" in filesystem_client.directories["d1"].files
    assert "GROUP_A" in filesystem_client.directories["d1"].files["a.txt"].acl
    assert "GROUP_B" not in filesystem_client.directories["d1"].files["a.txt"].acl
    assert "GROUP_C" in filesystem_client.directories["d1"].files["a.txt"].acl
    assert "c.txt" in filesystem_client.directories["d1"].files
    assert "GROUP_A" in filesystem_client.directories["d1"].files["c.txt"].acl
    assert "GROUP_B" not in filesystem_client.directories["d1"].files["c.txt"].acl
    assert "GROUP_C" in filesystem_client.directories["d1"].files["c.txt"].acl
    assert len(filesystem_client.directories["d2"].files) == 1
    assert "b.txt" in filesystem_client.directories["d2"].files
    assert "GROUP_A" in filesystem_client.directories["d2"].files["b.txt"].acl
    assert "GROUP_B" in filesystem_client.directories["d2"].files["b.txt"].acl
    assert "GROUP_C" in filesystem_client.directories["d2"].files["b.txt"].acl
    assert len(filesystem_client.directories["/"].files) == 0


@pytest.mark.asyncio
async def test_adls_gen2_create_group(
    monkeypatch, mock_data_lake_service_client, mock_adlsgen2setup, mock_get_group_missing, mock_put_group, mock_open
):
    command = AdlsGen2Setup(
        data_directory="",
        storage_account_name="STORAGE",
        filesystem_name="FILESYSTEM",
        security_enabled_groups=False,
        data_access_control_format=valid_data_access_control_format,
        credentials=MockAzureCredential(),
    )

    assert await command.create_or_get_group("GROUP_A") == "GROUP_A_ID_CREATED"
    assert await command.create_or_get_group("GROUP_B") == "GROUP_B_ID_CREATED"
    assert await command.create_or_get_group("GROUP_C") == "GROUP_C_ID_CREATED"
