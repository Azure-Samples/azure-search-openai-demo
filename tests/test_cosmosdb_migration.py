import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.cosmosdb_migration import CosmosDBMigrator, migrate_cosmosdb_data

# Sample old format item
TEST_OLD_ITEM = {
    "id": "123",
    "entra_oid": "OID_X",
    "title": "This is a test message",
    "timestamp": 123456789,
    "answers": [
        [
            "What does a Product Manager do?",
            {
                "delta": {"role": "assistant"},
                "session_state": "143c0240-b2ee-4090-8e90-2a1c58124894",
                "message": {
                    "content": "A Product Manager is responsible for product strategy and execution.",
                    "role": "assistant",
                },
            },
        ],
        [
            "What about a Software Engineer?",
            {
                "delta": {"role": "assistant"},
                "session_state": "243c0240-b2ee-4090-8e90-2a1c58124894",
                "message": {
                    "content": "A Software Engineer writes code to create applications.",
                    "role": "assistant",
                },
            },
        ],
    ],
}


class MockAsyncPageIterator:
    """Helper class to mock an async page from CosmosDB"""

    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


class MockCosmosDBResultsIterator:
    """Helper class to mock a paginated query result from CosmosDB"""

    def __init__(self, data=[]):
        self.data = data
        self.continuation_token = None

    def by_page(self, continuation_token=None):
        """Return a paged iterator"""
        self.continuation_token = "next_token" if not continuation_token else continuation_token + "_next"
        # Return an async iterator that contains pages
        return MockPagesAsyncIterator(self.data)


class MockPagesAsyncIterator:
    """Helper class to mock an iterator of pages"""

    def __init__(self, data):
        self.data = data
        self.continuation_token = "next_token"

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.data:
            raise StopAsyncIteration
        # Return a page, which is an async iterator of items
        return MockAsyncPageIterator([self.data.pop(0)])


@pytest.mark.asyncio
async def test_migrate_method():
    """Test the migrate method of CosmosDBMigrator"""
    # Create mock objects
    mock_container = MagicMock()
    mock_database = MagicMock()
    mock_client = MagicMock()

    # Set up the query_items mock to return our test item
    mock_container.query_items.return_value = MockCosmosDBResultsIterator([TEST_OLD_ITEM])

    # Set up execute_item_batch as a spy to capture calls
    execute_batch_mock = AsyncMock()
    mock_container.execute_item_batch = execute_batch_mock

    # Set up the database mock to return our container mocks
    mock_database.get_container_client.side_effect = lambda container_name: mock_container

    # Set up the client mock
    mock_client.get_database_client.return_value = mock_database

    # Create the migrator with our mocks
    migrator = CosmosDBMigrator("dummy_account", "dummy_db")
    migrator.client = mock_client
    migrator.database = mock_database
    migrator.old_container = mock_container
    migrator.new_container = mock_container

    # Call the migrate method
    await migrator.migrate()

    # Verify query_items was called with the right parameters
    mock_container.query_items.assert_called_once_with(query="SELECT * FROM c")

    # Verify execute_item_batch was called
    execute_batch_mock.assert_called_once()

    # Extract the arguments from the call
    call_args = execute_batch_mock.call_args[1]
    batch_operations = call_args["batch_operations"]
    partition_key = call_args["partition_key"]

    # Verify the partition key
    assert partition_key == ["OID_X", "123"]

    # We should have 3 operations: 1 for session and 2 for message pairs
    assert len(batch_operations) == 3

    # Verify session item
    session_operation = batch_operations[0]
    assert session_operation[0] == "upsert"
    session_item = session_operation[1][0]
    assert session_item["id"] == "123"
    assert session_item["session_id"] == "123"
    assert session_item["entra_oid"] == "OID_X"
    assert session_item["title"] == "This is a test message"
    assert session_item["timestamp"] == 123456789
    assert session_item["type"] == "session"
    assert session_item["version"] == "cosmosdb-v2"

    # Verify first message pair
    message1_operation = batch_operations[1]
    assert message1_operation[0] == "upsert"
    message1_item = message1_operation[1][0]
    assert message1_item["id"] == "123-0"
    assert message1_item["session_id"] == "123"
    assert message1_item["entra_oid"] == "OID_X"
    assert message1_item["question"] == "What does a Product Manager do?"
    assert message1_item["type"] == "message_pair"
    assert message1_item["order"] == 0

    # Verify second message pair
    message2_operation = batch_operations[2]
    assert message2_operation[0] == "upsert"
    message2_item = message2_operation[1][0]
    assert message2_item["id"] == "123-1"
    assert message2_item["session_id"] == "123"
    assert message2_item["entra_oid"] == "OID_X"
    assert message2_item["question"] == "What about a Software Engineer?"
    assert message2_item["type"] == "message_pair"
    assert message2_item["order"] == 1


@pytest.mark.asyncio
async def test_migrate_cosmosdb_data(monkeypatch):
    """Test the main migrate_cosmosdb_data function"""
    with patch.dict(os.environ, clear=True):
        monkeypatch.setenv("USE_CHAT_HISTORY_COSMOS", "true")
        monkeypatch.setenv("AZURE_COSMOSDB_ACCOUNT", "dummy_account")
        monkeypatch.setenv("AZURE_CHAT_HISTORY_DATABASE", "dummy_db")

        # Create a mock for the CosmosDBMigrator
        with patch("scripts.cosmosdb_migration.CosmosDBMigrator") as mock_migrator_class:
            # Set up the mock for the migrator instance
            mock_migrator = AsyncMock()
            mock_migrator_class.return_value = mock_migrator

            # Call the function
            await migrate_cosmosdb_data()

            # Verify the migrator was created with the right parameters
            mock_migrator_class.assert_called_once_with("dummy_account", "dummy_db")

            # Verify migrate and close were called
            mock_migrator.migrate.assert_called_once()
            mock_migrator.close.assert_called_once()
