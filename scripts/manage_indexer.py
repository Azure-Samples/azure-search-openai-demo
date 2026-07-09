"""Small helper to reset / run / get status for the cloud ingestion indexer.

Usage:
  python scripts/manage_indexer.py reset
  python scripts/manage_indexer.py run
  python scripts/manage_indexer.py status
  python scripts/manage_indexer.py wait      # poll status until not "inProgress"

The indexer name is derived from AZURE_SEARCH_INDEX to match
CloudIngestionStrategy in app/backend/prepdocslib/cloudingestionstrategy.py.
"""

import asyncio
import os
import sys

from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.indexes.aio import SearchIndexerClient

from load_azd_env import load_azd_env


async def main(action: str) -> None:
    load_azd_env()

    service = os.environ["AZURE_SEARCH_SERVICE"]
    index_name = os.environ["AZURE_SEARCH_INDEX"]
    # Keep indexer_name in sync with app/backend/prepdocslib/cloudingestionstrategy.py
    indexer_name = f"{index_name}-cloud-indexer"
    endpoint = f"https://{service}.search.windows.net"
    tenant_id = os.environ.get("AZURE_TENANT_ID")

    azd_credential = (
        AzureDeveloperCliCredential()
        if tenant_id is None
        else AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    )

    async with azd_credential, SearchIndexerClient(endpoint=endpoint, credential=azd_credential) as client:
        if action == "reset":
            await client.reset_indexer(indexer_name)
            print(f"reset {indexer_name}")
        elif action == "run":
            await client.run_indexer(indexer_name)
            print(f"run {indexer_name}")
        elif action == "status":
            status = await client.get_indexer_status(indexer_name)
            print_status(status)
        elif action == "wait":
            while True:
                status = await client.get_indexer_status(indexer_name)
                print_status(status)
                last = status.last_result
                if last is None or last.status not in ("inProgress",):
                    return
                await asyncio.sleep(15)
        else:
            raise SystemExit(f"unknown action: {action}")


def print_status(status) -> None:
    print("=" * 72)
    print(f"status={status.status}  lastStatus={status.last_result and status.last_result.status}")
    last = status.last_result
    if last is None:
        print("no last_result yet")
        return
    print(f"start={last.start_time}  end={last.end_time}")
    print(f"itemsProcessed={last.item_count}  itemsFailed={last.failed_item_count}")
    if last.error_message:
        print(f"errorMessage: {last.error_message}")
    for e in (last.errors or [])[:20]:
        print(f"  ERROR key={e.key} name={e.name} message={e.error_message}")
        if e.details:
            print(f"    details={e.details}")
    for w in (last.warnings or [])[:20]:
        print(f"  WARN  key={w.key} name={w.name} message={w.message}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "status"))
