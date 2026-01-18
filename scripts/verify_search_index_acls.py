"""
Test script for Azure AI Search elevated read permissions.
This script verifies that ACL filtering is working and tests elevated read access.
"""

import asyncio
import os

from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient

from load_azd_env import load_azd_env


async def main():
    load_azd_env()

    tenant_id = os.environ["AZURE_TENANT_ID"]
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    index_name = os.environ["AZURE_SEARCH_INDEX"]

    search_endpoint = f"https://{search_service}.search.windows.net"

    # Get credential
    print(f"Setting up Azure credential using AzureDeveloperCliCredential with tenant_id {tenant_id}")
    credential = AzureDeveloperCliCredential(tenant_id=tenant_id)

    # Get user token for ACL filtering (no "Bearer " prefix needed)
    token = await credential.get_token("https://search.azure.com/.default")
    user_token = token.token

    # 1. Get index statistics
    print(f"\n=== Index statistics for '{index_name}' ===")
    async with SearchIndexClient(endpoint=search_endpoint, credential=credential) as index_client:
        stats = await index_client.get_index_statistics(index_name)
        print(f"Document count: {stats['document_count']}")
        print(f"Storage size: {stats['storage_size']} bytes")

    async with SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential) as search_client:

        # Search WITHOUT user token (no ACL filtering header)
        print("\n=== Search without ACL headers/tokens ===")
        results_no_acl = await search_client.search(
            search_text="*",
            top=5,
            select=["id", "sourcefile"],
            include_total_count=True,
        )
        docs_no_acl = [doc async for doc in results_no_acl]
        print(f"Results returned: {len(docs_no_acl)}")
        print(f"Total count: {await results_no_acl.get_count()}")
        for doc in docs_no_acl:
            print(f"  - {doc.get('sourcefile')}")

        # Search WITH user token:
        # This enables automatic ACL filtering based on the user's identity
        print("\n=== Search with ACL header and token (x-ms-query-source-authorization) ===")
        results = await search_client.search(
            search_text="*",
            top=5,
            select=["id", "sourcefile"],
            include_total_count=True,
            x_ms_query_source_authorization=user_token,  # No "Bearer " prefix!
        )
        docs = [doc async for doc in results]
        print(f"Results returned: {len(docs)}")
        print(f"Total count: {await results.get_count()}")
        for doc in docs:
            print(f"  - {doc.get('sourcefile')}")

        # Search with elevated read (bypasses ACL filtering - for debugging)
        print("\n=== Search with elevated read header (x-ms-enable-elevated-read) ===")
        elevated_results = await search_client.search(
            search_text="*",
            top=5,
            select=["id", "sourcefile", "oids", "groups"],
            include_total_count=True,
            x_ms_enable_elevated_read=True,
        )
        elevated_docs = [doc async for doc in elevated_results]
        print(f"Results returned: {len(elevated_docs)}")
        print(f"Total count: {await elevated_results.get_count()}")
        for doc in elevated_docs:
            print(f"  - {doc.get('sourcefile')}")
            print(f"    oids: {doc.get('oids', [])}")
            print(f"    groups: {doc.get('groups', [])}")


if __name__ == "__main__":
    asyncio.run(main())
