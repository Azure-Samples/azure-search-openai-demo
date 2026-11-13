"""Approves the private endpoint connections that the search service's shared private links create.

With AZURE_USE_PRIVATE_ENDPOINT and USE_CLOUD_INGESTION_BUILTIN, the deployment creates shared private links
from Azure AI Search to the storage and AI services accounts. Each link creates a pending private endpoint
connection on the target resource, which only the target's owner can approve. The connection names include
a generated ID, so they can't be approved in Bicep.
"""

import asyncio
import logging
import os
from typing import Any

import aiohttp
from azure.identity.aio import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env

logger = logging.getLogger("scripts")

ARM_ENDPOINT = "https://management.azure.com"
SEARCH_API_VERSION = "2025-05-01"
# Private endpoint connections API version, supported by both storage and Cognitive Services accounts
CONNECTION_API_VERSION = "2025-06-01"
APPROVAL_TIMEOUT_SECONDS = 600
POLL_INTERVAL_SECONDS = 15
MAX_ATTEMPTS = 4


async def arm_request(session: aiohttp.ClientSession, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    """Sends an ARM request, retrying server errors such as the occasional 504 from the search resource provider."""
    attempt = 1
    while True:
        async with session.request(method, url, **kwargs) as response:
            if response.status < 500 or attempt == MAX_ATTEMPTS:
                response.raise_for_status()
                return await response.json()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        attempt += 1


def connections_to_approve(link_name: str, connections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Returns the pending connections on a target resource that belong to the given shared private link.

    Azure AI Search names the private endpoint behind each shared private link after the link.
    """
    return [
        connection
        for connection in connections
        if connection["properties"]["privateEndpoint"]["id"].lower().endswith(f"/privateendpoints/{link_name}".lower())
        and connection["properties"]["privateLinkServiceConnectionState"]["status"] == "Pending"
    ]


async def list_shared_private_links(session: aiohttp.ClientSession, search_service_id: str) -> list[dict[str, Any]]:
    url = f"{ARM_ENDPOINT}{search_service_id}/sharedPrivateLinkResources?api-version={SEARCH_API_VERSION}"
    return (await arm_request(session, "GET", url))["value"]


async def approve_links(session: aiohttp.ClientSession, links: list[dict[str, Any]]) -> None:
    for link in links:
        properties = link["properties"]
        if properties["status"] != "Pending":
            continue
        target_id = properties["privateLinkResourceId"]
        api_version = CONNECTION_API_VERSION
        connections = (
            await arm_request(
                session, "GET", f"{ARM_ENDPOINT}{target_id}/privateEndpointConnections?api-version={api_version}"
            )
        )["value"]
        for connection in connections_to_approve(link["name"], connections):
            logger.info("Approving %s on %s", link["name"], target_id.split("/")[-1])
            body = {
                "properties": {
                    "privateLinkServiceConnectionState": {
                        "status": "Approved",
                        "description": "Approved by azd for Azure AI Search indexer access",
                    },
                }
            }
            await arm_request(session, "PUT", f"{ARM_ENDPOINT}{connection['id']}?api-version={api_version}", json=body)


async def wait_for_approval(session: aiohttp.ClientSession, search_service_id: str) -> None:
    elapsed = 0
    while elapsed < APPROVAL_TIMEOUT_SECONDS:
        links = await list_shared_private_links(session, search_service_id)
        failed = [link["name"] for link in links if link["properties"]["provisioningState"] == "Failed"]
        if failed:
            # A failed link never becomes approved; deleting it and running azd provision again recreates it
            logger.error(
                "Shared private links failed to provision: %s. Delete them from the search service's "
                "Networking page and run 'azd provision' again.",
                ", ".join(failed),
            )
            return
        # Approval propagates from the target resource to the search service asynchronously
        pending = [
            link["name"]
            for link in links
            if link["properties"]["status"] != "Approved" or link["properties"]["provisioningState"] != "Succeeded"
        ]
        if not pending:
            logger.info("All %d shared private links are approved", len(links))
            return
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
    logger.warning("Shared private links still not approved after %d minutes: %s", elapsed // 60, ", ".join(pending))


async def main() -> None:
    load_azd_env(override=os.getenv("LOADING_MODE_FOR_AZD_ENV_VARS") != "no-override")
    if os.getenv("AZURE_USE_PRIVATE_ENDPOINT", "").lower() != "true" or not (
        os.getenv("USE_CLOUD_INGESTION", "").lower() == "true"
        and os.getenv("USE_CLOUD_INGESTION_BUILTIN", "").lower() == "true"
    ):
        return

    search_service_id = (
        f"/subscriptions/{os.environ['AZURE_SUBSCRIPTION_ID']}"
        f"/resourceGroups/{os.environ['AZURE_SEARCH_SERVICE_RESOURCE_GROUP']}"
        f"/providers/Microsoft.Search/searchServices/{os.environ['AZURE_SEARCH_SERVICE']}"
    )
    async with AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID", "")) as credential:
        token = await credential.get_token(f"{ARM_ENDPOINT}/.default")
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {token.token}"}) as session:
            await approve_links(session, await list_shared_private_links(session, search_service_id))
            await wait_for_approval(session, search_service_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logger.setLevel(logging.INFO)
    asyncio.run(main())
