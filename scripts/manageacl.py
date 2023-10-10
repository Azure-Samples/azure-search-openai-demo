import argparse
import asyncio
import json
import logging
from typing import Any, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchFieldDataType,
    SimpleField,
)


class ManageAcl:
    """
    Manually enable document level access control on a search index and manually set access control values using the [manageacl.ps1](./scripts/manageacl.ps1) script.
    """

    def __init__(
        self,
        service_name: str,
        index_name: str,
        document: str,
        acl_action: str,
        acl_type: str,
        acl: str,
        credentials: Union[AsyncTokenCredential, AzureKeyCredential],
    ):
        """
        Initializes the command

        Parameters
        ----------
        service_name
            Name of the Azure Search service
        index_name
            Name of the Azure Search index
        document
            File path of the document to manage acls for
        acl_action
            Action to take regarding the index or document. Valid values include enable_acls (turn acls on for the entire index), view (print acls for the document), remove_all (remove all acls), remove (remove a specific acl), or add (add a specific acl)
        acl_type
            Type of acls to manage. Valid values include groups or oids.
        acl
            The actual value of the acl, if the acl action is add or remove
        credentials
            Credentials for the azure search service
        """
        self.service_name = service_name
        self.index_name = index_name
        self.credentials = credentials
        self.document = document
        self.acl_action = acl_action
        self.acl_type = acl_type
        self.acl = acl

    async def run(self):
        endpoint = f"https://{self.service_name}.search.windows.net"
        if self.acl_action == "enable_acls":
            await self.enable_acls(endpoint)
            return

        async with SearchClient(
            endpoint=endpoint, index_name=self.index_name, credential=self.credentials
        ) as search_client:
            if self.acl_action == "view":
                await self.view_acl(search_client)
            elif self.acl_action == "remove":
                await self.remove_acl(search_client)
            elif self.acl_action == "remove_all":
                await self.remove_all_acls(search_client)
            elif self.acl_action == "add":
                await self.add_acl(search_client)
            else:
                raise Exception(f"Unknown action {self.acl_action}")

            logging.info("ACLs updated")

    async def view_acl(self, search_client: SearchClient):
        async for document in await self.get_documents(search_client):
            # Assumes the acls are consistent across all sections of the document
            print(json.dumps(document[self.acl_type]))
            return

    async def remove_acl(self, search_client: SearchClient):
        documents_to_merge = []
        async for document in await self.get_documents(search_client):
            new_acls = [acl_value for acl_value in document[self.acl_type] if acl_value != self.acl]
            documents_to_merge.append({"id": document["id"], self.acl_type: new_acls})

        if len(documents_to_merge) > 0:
            await search_client.merge_documents(documents=documents_to_merge)

    async def remove_all_acls(self, search_client: SearchClient):
        documents_to_merge = []
        async for document in await self.get_documents(search_client):
            documents_to_merge.append({"id": document["id"], self.acl_type: []})

        if len(documents_to_merge) > 0:
            await search_client.merge_documents(documents=documents_to_merge)

    async def add_acl(self, search_client: SearchClient):
        documents_to_merge = []
        async for document in await self.get_documents(search_client):
            new_acls = document[self.acl_type]
            if not any(acl_value == self.acl for acl_value in new_acls):
                new_acls.append(self.acl)
            documents_to_merge.append({"id": document["id"], self.acl_type: new_acls})

        if len(documents_to_merge) > 0:
            await search_client.merge_documents(documents=documents_to_merge)

    async def get_documents(self, search_client: SearchClient):
        filter = f"sourcefile eq '{self.document}'"
        result = await search_client.search("", filter=filter, select=["id", self.acl_type])
        return result

    async def enable_acls(self, endpoint: str):
        async with SearchIndexClient(endpoint=endpoint, credential=self.credentials) as search_index_client:
            logging.info(f"Enabling acls for index {self.index_name}")
            index_definition = await search_index_client.get_index(self.index_name)
            if not any(field.name == "oids" for field in index_definition.fields):
                index_definition.fields.append(
                    SimpleField(
                        name="oids",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        filterable=True,
                    )
                )
            if not any(field.name == "groups" for field in index_definition.fields):
                index_definition.fields.append(
                    SimpleField(
                        name="groups",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        filterable=True,
                    )
                )

            await search_index_client.create_or_update_index(index_definition)


async def main(args: Any):
    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = (
        AzureDeveloperCliCredential()
        if args.tenant_id is None
        else AzureDeveloperCliCredential(tenant_id=args.tenant_id, process_timeout=60)
    )
    search_credential: Union[AsyncTokenCredential, AzureKeyCredential] = azd_credential
    if args.search_key is not None:
        search_credential = AzureKeyCredential(args.search_key)

    command = ManageAcl(
        service_name=args.search_service,
        index_name=args.index,
        document=args.document,
        acl_action=args.acl_action,
        acl_type=args.acl_type,
        acl=args.acl,
        credentials=search_credential,
    )
    await command.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage ACLs in a search index",
        epilog="Example: manageacl.py --searchservice mysearch --index myindex --acl-action enable_acls",
    )
    parser.add_argument(
        "--search-service",
        required=True,
        help="Name of the Azure Cognitive Search service where content should be indexed (must exist already)",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="Name of the Azure Cognitive Search index where content should be indexed (will be created if it doesn't exist)",
    )
    parser.add_argument(
        "--search-key",
        required=False,
        help="Optional. Use this Azure Cognitive Search account key instead of the current user identity to login (use az login to set current user for Azure)",
    )
    parser.add_argument("--acl-type", required=False, choices=["oids", "groups"], help="Optional. Type of ACL")
    parser.add_argument(
        "--acl-action",
        required=False,
        choices=["remove", "add", "view", "remove_all", "enable_acls"],
        help="Optional. Whether to remove or add the ACL to the document, or enable acls on the index",
    )
    parser.add_argument("--acl", required=False, default=None, help="Optional. Value of ACL to add or remove.")
    parser.add_argument("--document", required=False, help="Optional. Name of document to update ACLs for")
    parser.add_argument(
        "--tenant-id", required=False, help="Optional. Use this to define the Azure directory where to authenticate)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)

    if not args.acl_type and args.acl_action != "enable_acls":
        print("Must specify either --acl-type or --acl-action enable_acls")
        exit(1)

    asyncio.run(main(args))
