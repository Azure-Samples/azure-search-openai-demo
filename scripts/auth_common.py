import os
from typing import Dict, Optional

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential

TIMEOUT = 60


async def get_auth_headers(credential: AsyncTokenCredential):
    token_result = await credential.get_token("https://graph.microsoft.com/.default")
    return {"Authorization": f"Bearer {token_result.token}"}


async def get_application(auth_headers: Dict[str, str], app_id: str) -> Optional[str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(f"https://graph.microsoft.com/v1.0/applications(appId='{app_id}')") as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json["id"]

    return None


async def update_application(auth_headers: Dict[str, str], object_id: str, app_payload: object):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.patch(
            f"https://graph.microsoft.com/v1.0/applications/{object_id}", json=app_payload
        ) as response:
            if not response.ok:
                response_json = await response.json()
                raise Exception(response_json)

    return True


def test_authentication_enabled():
    use_authentication = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    require_access_control = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    if require_access_control and not use_authentication:
        print("AZURE_ENFORCE_ACCESS_CONTROL is true, but AZURE_USE_AUTHENTICATION is false. Stopping...")
        return False

    if not use_authentication:
        return False

    return True
