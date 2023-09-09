from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchFieldDataType
)
import argparse
from azure.identity import AzureDeveloperCliCredential
from azure.core.credentials import AzureKeyCredential, TokenCredential

def enable_acls(credential: AzureKeyCredential|TokenCredential, search_service: str, index: str):
    index_client = SearchIndexClient(
        endpoint=f"https://{args.search_service}.search.windows.net/",
        credential=credential)
    if args.verbose: print(f"Enabling acls for index {index}")
    try:
        index_definition = index_client.get_index(index)
        if not any(field.name == 'oids' for field in index_definition.fields):
            index_definition.fields.append(SimpleField(name="oids", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True))
        if not any(field.name == 'groups' for field in index_definition.fields):
            index_definition.fields.append(SimpleField(name="groups", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True))
        
        index_client.create_or_update_index(index_definition)
    except Exception as e:
        print(f"\tGot an error while updating index {index} -> {e} --> unable to enable acls")

def update_acl(credential: AzureKeyCredential|TokenCredential, search_service: str, index: str, acl_type: str, acl_action: str, document: str, acl: str = None):
    search_client = SearchClient(
        endpoint=f"https://{args.search_service}.search.windows.net/",
        credential=credential,
        index_name=index
    )
    filter = f"sourcefile eq '{document}'"
    result = search_client.search("", filter=filter, select=["id", acl_type], include_total_count=True)
    if result.get_count() == 0:
        if args.verbose: print(F"No documents match {document} - exiting")
        return


    
    documents_to_merge = []
    for document in result:
        if acl_action == "view":
            # Assumes the acls are consistent across all sections of the document
            print(document[acl_type])
            return

        if acl_action == "remove":
            new_acls = [acl_value for acl_value in document[acl_type] if acl_value != acl]
        elif acl_action == "add":
            new_acls = document[acl_type]
            if not any(acl_value == acl for acl_value in new_acls):
                new_acls.append(acl)
        else:
            new_acls = []
        documents_to_merge.append({"id": document["id"], acl_type: new_acls})

    r = search_client.merge_documents(documents=documents_to_merge)
    if args.verbose: print(F"ACLs updated")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Manage ACLs in a search index",
        epilog="Example: manageacl.py --searchservice mysearch --index myindex --enable-acls"
        )
    parser.add_argument("--search-service", required=True, help="Name of the Azure Cognitive Search service where content should be indexed (must exist already)")
    parser.add_argument("--index", required=True, help="Name of the Azure Cognitive Search index where content should be indexed (will be created if it doesn't exist)")
    parser.add_argument("--search-key", required=False, help="Optional. Use this Azure Cognitive Search account key instead of the current user identity to login (use az login to set current user for Azure)")
    parser.add_argument("--enable-acls", required=False, action="store_true", help="Optional. Adds fields required for ACL management to the search index if they aren't already-present")
    parser.add_argument("--acl-type", required=False, choices=["oids", "groups"], help="Optional. Type of ACL")
    parser.add_argument("--acl-action", required=False, choices=["remove", "add", "view", "remove_all"], help="Optional. Whether to remove or add the ACL to the document")
    parser.add_argument("--acl", required=False, default=None, help="Optional. Value of ACL to add or remove.")
    parser.add_argument("--document", required=False, help="Optional. Name of document to update ACLs for")
    parser.add_argument("--tenant-id", required=False, help="Optional. Use this to define the Azure directory where to authenticate)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
    azd_credential = AzureDeveloperCliCredential() if args.tenant_id is None else AzureDeveloperCliCredential(tenant_id=args.tenant_id, process_timeout=60)
    search_credential = azd_credential if args.search_key is None else AzureKeyCredential(args.search_key)

    if args.enable_acls:
        enable_acls(search_credential, args.search_service, args.index)
    elif args.acl_type and args.acl_action and args.document:
        if args.acl_action in ["remove", "add"] and args.acl is None:
            print("Error: --acl must be specified if --acl-action is remove or add")
            exit(1)

        update_acl(search_credential, args.search_service, args.index, args.acl_type, args.acl_action, args.document, args.acl)
    else:
        print("Error: Specify either --enable-acls or --acl-type [type] --acl-action [action] --document [document] [--acl acl_value]")