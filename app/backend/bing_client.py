"""
An async client for Bing Web Search API.
"""

from typing import Optional, Union

import httpx
from pydantic import BaseModel, ConfigDict


class WebPage(BaseModel):
    id: str
    name: str
    url: str
    displayUrl: str
    dateLastCrawled: str
    language: str
    snippet: Optional[str] = None
    isFamilyFriendly: Optional[bool] = True
    siteName: Optional[str] = None

    # There are more fields in the response, but we only care about these for now.
    model_config = ConfigDict(
        extra="allow",
    )


class WebAnswer(BaseModel):
    totalEstimatedMatches: int
    value: list[WebPage]
    webSearchUrl: str

    # There are more fields in the response, but we only care about these for now.
    model_config = ConfigDict(
        extra="allow",
    )


class AsyncBingClient:
    def __init__(self, api_key: str, bing_endpoint: Optional[str] = "api.bing.microsoft.com"):
        self.api_key = api_key
        self.base_url = f"https://{bing_endpoint}/v7.0/search"
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "User-Agent": "azure-search-openai-demo",
            # "X-Search-Location": "" # this would be useful in future
        }

    async def search(self, query: str, lang="en-US") -> WebAnswer:
        params: dict[str, Union[str, bool, int]] = {
            "q": query,
            "mkt": lang,
            "textDecorations": True,
            "textFormat": "HTML",
            "responseFilter": "Webpages",
            "safeSearch": "Strict",
            "setLang": lang,
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            return WebAnswer.model_validate(response.json()["webPages"])
