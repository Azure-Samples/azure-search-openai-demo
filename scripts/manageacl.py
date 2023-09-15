import argparse
import asyncio
import logging

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import SearchFieldDataType, SimpleField


class ManageAcl:
    def __init__(
        self,
        service_name: str,
        index_name: str,
        document: str,
        acl_action: str,
        acl_type: str,
        acl: str,
        credentials: AsyncTokenCredential | AzureKeyCredential,
    ):
        self.service_name = service_name
        self.index_name = index_name
        self.credentials = credentials
        self.document = document
        self.acl_action = acl_action
        self.acl_type = acl_type
        self.acl = acl

    async def run(self):
        endpoint = f"https://{self.service_name}.search.windows.net"
        async with SearchClient(
            endpoint=endpoint, credential=self.credentials, index_name=self.index_name
        ), SearchIndexClient(endpoint=endpoint, credential=self.credentials):
            if self.acl_action == "enable_acls":
                logging.info(f"Enabling acls for index {self.index_name}")
                index_definition = await self.search_index_client.get_index(self.index_name)
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

                await self.search_index_client.create_or_update_index(index_definition)
                return

            filter = f"sourcefile eq '{self.document}'"
            result = await self.search_client.search(
                "", filter=filter, select=["id", self.acl_type], include_total_count=True
            )
            if await result.get_count() == 0:
                logging.info(f"No documents match {self.document} - exiting")
                return

            documents_to_merge = []
            async for document in result:
                if self.acl_action == "view":
                    # Assumes the acls are consistent across all sections of the document
                    print(document[self.acl_type])
                    return

                if self.acl_action == "remove":
                    new_acls = [acl_value for acl_value in document[self.acl_type] if acl_value != self.acl]
                elif self.acl_action == "add":
                    new_acls = document[self.acl_type]
                    if not any(acl_value == self.acl for acl_value in new_acls):
                        new_acls.append(self.acl)
                else:
                    new_acls = []
                documents_to_merge.append({"id": document["id"], self.acl_type: new_acls})

            await self.search_client.merge_documents(documents=documents_to_merge)
            logging.info("ACLs updated")


async def main(args: any):
    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = (
        AzureDeveloperCliCredential()
        if args.tenant_id is None
        else AzureDeveloperCliCredential(tenant_id=args.tenant_id, process_timeout=60)
    )
    search_credential = azd_credential if args.search_key is None else AzureKeyCredential(args.search_key)

    async with ManageAcl(
        service_name=args.search_service,
        index_name=args.index,
        document=args.document,
        acl_action=args.acl_action,
        acl_type=args.acl_type,
        acl=args.acl,
        credentials=search_credential,
        verbose=args.verbose,
    ) as command:
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
