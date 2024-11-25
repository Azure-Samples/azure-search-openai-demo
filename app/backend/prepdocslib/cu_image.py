import logging
from typing import Union

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from rich.progress import Progress
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = logging.getLogger("scripts")

CU_API_VERSION = "2024-12-01-preview"

PATH_ANALYZER_MANAGEMENT = "/analyzers/{analyzerId}"
PATH_ANALYZER_MANAGEMENT_OPERATION = "/analyzers/{analyzerId}/operations/{operationId}"

# Define Analyzer inference paths
PATH_ANALYZER_INFERENCE = "/analyzers/{analyzerId}:analyze"
PATH_ANALYZER_INFERENCE_GET_IMAGE = "/analyzers/{analyzerId}/results/{operationId}/images/{imageId}"

analyzer_name = "image_analyzer"
image_schema = {
    "analyzerId": analyzer_name,
    "name": "Image understanding",
    "description": "Extract detailed structured information from images extracted from documents.",
    "baseAnalyzerId": "prebuilt-image",
    "scenario": "image",
    "config": {"returnDetails": False},
    "fieldSchema": {
        "name": "ImageInformation",
        "descriptions": "Description of image.",
        "fields": {
            "Description": {
                "type": "string",
                "description": "Description of the image. If the image has a title, start with the title. Include a 2-sentence summary. If the image is a chart, diagram, or table, include the underlying data in an HTML table tag, with accurate numbers. If the image is a chart, describe any axis or legends. The only allowed HTML tags are the table/thead/tr/td/tbody tags.",
            },
        },
    },
}


class ContentUnderstandingManager:

    def __init__(self, endpoint: str, credential: Union[AsyncTokenCredential, str]):
        self.endpoint = endpoint
        self.credential = credential

    async def poll_api(self, session, poll_url, headers):

        @retry(stop=stop_after_attempt(60), wait=wait_fixed(2), retry=retry_if_exception_type(ValueError))
        async def poll():
            async with session.get(poll_url, headers=headers) as response:
                response.raise_for_status()
                response_json = await response.json()
                if response_json["status"] == "Failed":
                    raise Exception("Failed")
                if response_json["status"] == "Running":
                    raise ValueError("Running")
                return response_json

        return await poll()

    async def create_analyzer(self):
        logger.info("Creating analyzer '%s'...", image_schema["analyzerId"])

        token_provider = get_bearer_token_provider(self.credential, "https://cognitiveservices.azure.com/.default")
        token = await token_provider()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        params = {"api-version": CU_API_VERSION}
        analyzer_id = image_schema["analyzerId"]
        cu_endpoint = f"{self.endpoint}/contentunderstanding/analyzers/{analyzer_id}"
        async with aiohttp.ClientSession() as session:
            async with session.put(url=cu_endpoint, params=params, headers=headers, json=image_schema) as response:
                if response.status == 409:
                    logger.info("Analyzer '%s' already exists.", analyzer_id)
                    return
                elif response.status != 201:
                    data = await response.text()
                    logger.error("Error creating analyzer: %s", data)
                    response.raise_for_status()
                else:
                    poll_url = response.headers.get("Operation-Location")

            with Progress() as progress:
                progress.add_task("Creating analyzer...", total=None, start=False)
                await self.poll_api(session, poll_url, headers)

    async def describe_image(self, image_bytes) -> str:
        logger.info("Sending image to Azure Content Understanding service...")
        async with aiohttp.ClientSession() as session:
            token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {"Authorization": "Bearer " + token.token}
            params = {"api-version": CU_API_VERSION}

            async with session.post(
                url=f"{self.endpoint}/contentunderstanding/analyzers/{analyzer_name}:analyze",
                params=params,
                headers=headers,
                data=image_bytes,
            ) as response:
                response.raise_for_status()
                poll_url = response.headers["Operation-Location"]

                with Progress() as progress:
                    progress.add_task("Processing...", total=None, start=False)
                    results = await self.poll_api(session, poll_url, headers)

                fields = results["result"]["contents"][0]["fields"]
                return fields["DescriptionHTML"]["valueString"]
