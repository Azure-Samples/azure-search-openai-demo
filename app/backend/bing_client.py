"""
An async client for Bing Web Search API
"""

import httpx
from pydantic import BaseModel
from typing import Any


class WebPage(BaseModel):
    about: Any
    dateLastCrawled: str
    datePublished: str
    datePublishedDisplayText: str
    contractualRules: Any
    deepLinks: Any
    displayUrl: str
    id: str
    isFamilyFriendly: bool
    isNavigational: bool
    language: str
    malware: Any
    name: str
    mentions: Any
    searchTags: Any
    snippet: str
    url: str


class WebAnswer(BaseModel):
    id: str
    someResultsRemoved: bool
    totalEstimatedMatches: int
    value: list[WebPage]
    webSearchUrl: str


class AsyncBingClient:
    def __init__(self, api_key: str, bing_endpoint: Optional[str] = "api.bing.microsoft.com"):
        self.api_key = api_key
        self.base_url = f"https://{bing_endpoint}/v7.0/search"
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "User-Agent": "azure-search-openai-demo",
            # "X-Search-Location": "" # this would be useful in future
        }
    
    async def search(self, query: str) -> WebAnswer:
        params = {
            "q": query,
            "textDecorations": True,
            "textFormat": "HTML",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            return WebAnswer.model_validate(response.json()['webPages'])
