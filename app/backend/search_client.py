"""
An async client for Bing Web Search API.
"""

from typing import Optional, Union

import httpx
from pydantic import BaseModel, ConfigDict
from azure.ai.projects.aio import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import BingGroundingTool


BING_CONNECTION_NAME = 'antbingtesting'

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


class AsyncGroundingSearchClient:
    project_client: AIProjectClient
    bing_tool: BingGroundingTool
    agent_id: str = "asst_u8x2Hb9c9stVQwQMbostJ8JK"

    def __init__(self, api_key: str, endpoint: Optional[str] = None):
        self.connection_string = endpoint


    async def search(self, query: str, lang="en-US") -> WebAnswer:
        cred = DefaultAzureCredential()
        # endpoint is the connection string
        self.project_client = AIProjectClient.from_connection_string(self.connection_string, cred)

        async with self.project_client:
            # Create thread for communication
            thread = await self.project_client.agents.create_thread()

            # Create message to thread
            message = await self.project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=query,
            )

            # Create and process agent run in thread with tools
            run = await self.project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=self.agent_id)

            if run.status == "failed":
                raise Exception(run.last_error)

            # Fetch and log all messages
            messages = await self.project_client.agents.list_messages(thread_id=thread.id)

            print(f"Messages: {messages}")

            run_steps = await self.project_client.agents.list_run_steps(run_id=run.id, thread_id=thread.id)
            run_steps_data = run_steps['data']
            print(run_steps_data)

            url = messages.data[0].content[0].text.annotations[0].as_dict()['url_citation']['url']
            title = messages.data[0].content[0].text.annotations[0].as_dict()['url_citation']['title']
            snippet = messages.data[0].content[0].text.value


        return WebAnswer(
                totalEstimatedMatches=1,
                webSearchUrl="https://www.bing.com",
                value=[
                    WebPage(
                        id="1",
                        name=title,
                        url=url,
                        displayUrl=url,
                        dateLastCrawled="2021-10-01",
                        language="en",
                        snippet=snippet,
                        isFamilyFriendly=True,
                        siteName="Bing"
                    )
                ],
            )

class AsyncBingSearchClient(AsyncGroundingSearchClient):
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
