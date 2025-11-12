import aiohttp
from typing import List, Dict, Any


class SerperClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search(self, query: str, top: int = 5) -> List[Dict[str, Any]]:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": top}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"SERPER API error {resp.status}: {error_text}")
                data = await resp.json()
                return data.get("organic", []) or []


