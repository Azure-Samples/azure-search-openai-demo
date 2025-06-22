import asyncio
import os
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents.indexes.aio import SearchIndexClient

async def delete_search_index():
    # Load environment variables
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    index_name = "gptkbindex"  # or os.environ["AZURE_SEARCH_INDEX"]
    
    # Setup credentials
    azd_credential = AzureDeveloperCliCredential()
    
    # Create search index client
    endpoint = f"https://{search_service}.search.windows.net/"
    
    async with SearchIndexClient(endpoint=endpoint, credential=azd_credential) as client:
        try:
            await client.delete_index(index_name)
            print(f"Successfully deleted search index: {index_name}")
        except Exception as e:
            print(f"Error deleting index: {e}")

if __name__ == "__main__":
    asyncio.run(delete_search_index())