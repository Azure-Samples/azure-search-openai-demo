"""
A migration script to migrate data from CosmosDB to a new format.
The old schema:
id: str
entra_oid: str
title: str
timestamp: int
answers: list of 2-item list of str, dict

The new schema has two item types in the same container:
For session items:
id: str
session_id: str
entra_oid: str
title: str
timestamp: int
type: str (always "session")
version: str (always "cosmosdb-v2")

For message_pair items:
id: str
session_id: str
entra_oid: str
type: str (always "message_pair")
version: str (always "cosmosdb-v2")
question: str
response: dict
"""

import os

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import AzureDeveloperCliCredential

from load_azd_env import load_azd_env


class CosmosDBMigrator:
    """
    Migrator class for CosmosDB data migration.
    """

    def __init__(self, cosmos_account, database_name, credential=None):
        """
        Initialize the migrator with CosmosDB account and database.

        Args:
            cosmos_account: CosmosDB account name
            database_name: Database name
            credential: Azure credential, defaults to AzureDeveloperCliCredential
        """
        self.cosmos_account = cosmos_account
        self.database_name = database_name
        self.credential = credential or AzureDeveloperCliCredential()
        self.client = None
        self.database = None
        self.old_container = None
        self.new_container = None

    async def connect(self):
        """
        Connect to CosmosDB and initialize containers.
        """
        self.client = CosmosClient(
            url=f"https://{self.cosmos_account}.documents.azure.com:443/", credential=self.credential
        )
        self.database = self.client.get_database_client(self.database_name)
        self.old_container = self.database.get_container_client("chat-history")
        self.new_container = self.database.get_container_client("chat-history-v2")
        try:
            await self.old_container.read()
        except Exception:
            raise ValueError(f"Old container {self.old_container.id} does not exist")
        try:
            await self.new_container.read()
        except Exception:
            raise ValueError(f"New container {self.new_container.id} does not exist")

    async def migrate(self):
        """
        Migrate data from old schema to new schema.
        """
        if not self.client:
            await self.connect()
        if not self.old_container or not self.new_container:
            raise ValueError("Containers do not exist")

        query_results = self.old_container.query_items(query="SELECT * FROM c")

        item_migration_count = 0
        async for page in query_results.by_page():
            async for old_item in page:
                batch_operations = []
                # Build session item
                session_item = {
                    "id": old_item["id"],
                    "version": "cosmosdb-v2",
                    "session_id": old_item["id"],
                    "entra_oid": old_item["entra_oid"],
                    "title": old_item.get("title"),
                    "timestamp": old_item.get("timestamp"),
                    "type": "session",
                }
                batch_operations.append(("upsert", (session_item,)))

                # Build message_pair
                answers = old_item.get("answers", [])
                for idx, answer in enumerate(answers):
                    question = answer[0]
                    response = answer[1]
                    message_pair = {
                        "id": f"{old_item['id']}-{idx}",
                        "version": "cosmosdb-v2",
                        "session_id": old_item["id"],
                        "entra_oid": old_item["entra_oid"],
                        "type": "message_pair",
                        "question": question,
                        "response": response,
                        "order": idx,
                        "timestamp": None,
                    }
                    batch_operations.append(("upsert", (message_pair,)))

                # Execute the batch using partition key [entra_oid, session_id]
                await self.new_container.execute_item_batch(
                    batch_operations=batch_operations, partition_key=[old_item["entra_oid"], old_item["id"]]
                )
                item_migration_count += 1
        print(f"Total items migrated: {item_migration_count}")

    async def close(self):
        """
        Close the CosmosDB client.
        """
        if self.client:
            await self.client.close()


async def migrate_cosmosdb_data():
    """
    Legacy function for backward compatibility.
    Migrate data from CosmosDB to a new format.
    """
    USE_CHAT_HISTORY_COSMOS = os.getenv("USE_CHAT_HISTORY_COSMOS", "").lower() == "true"
    if not USE_CHAT_HISTORY_COSMOS:
        raise ValueError("USE_CHAT_HISTORY_COSMOS must be set to true")
    AZURE_COSMOSDB_ACCOUNT = os.environ["AZURE_COSMOSDB_ACCOUNT"]
    AZURE_CHAT_HISTORY_DATABASE = os.environ["AZURE_CHAT_HISTORY_DATABASE"]

    migrator = CosmosDBMigrator(AZURE_COSMOSDB_ACCOUNT, AZURE_CHAT_HISTORY_DATABASE)
    try:
        await migrator.migrate()
    finally:
        await migrator.close()


if __name__ == "__main__":
    load_azd_env()

    import asyncio

    asyncio.run(migrate_cosmosdb_data())
