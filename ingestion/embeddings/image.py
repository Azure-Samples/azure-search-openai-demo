"""
Image embedding generation using Azure AI Vision.

This module provides the ImageEmbeddings class for generating image embeddings
using Azure AI Vision's vectorization API.
"""

import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin

import aiohttp
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger("ingestion")


class ImageEmbeddings:
    """
    Class for using image embeddings from Azure AI Vision.
    To learn more, please visit https://learn.microsoft.com/azure/ai-services/computer-vision/how-to/image-retrieval#call-the-vectorize-image-api

    Attributes:
        endpoint: Azure AI Vision endpoint URL
        token_provider: Async function that returns a bearer token
    """

    def __init__(self, endpoint: str, token_provider: Callable[[], Awaitable[str]]):
        """
        Initialize the ImageEmbeddings client.

        Args:
            endpoint: Azure AI Vision endpoint URL
            token_provider: Async function that returns a bearer token
        """
        self.token_provider = token_provider
        self.endpoint = endpoint

    async def create_embedding_for_image(self, image_bytes: bytes) -> list[float]:
        """Create an embedding vector for an image.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Embedding vector as a list of floats

        Raises:
            ValueError: If embedding creation fails after retries
        """
        endpoint = urljoin(self.endpoint, "computervision/retrieval:vectorizeImage")
        params = {"api-version": "2024-02-01", "model-version": "2023-04-15"}
        headers = {"Authorization": "Bearer " + await self.token_provider()}

        async with aiohttp.ClientSession(headers=headers) as session:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(Exception),
                wait=wait_random_exponential(min=15, max=60),
                stop=stop_after_attempt(15),
                before_sleep=self.before_retry_sleep,
            ):
                with attempt:
                    async with session.post(url=endpoint, params=params, data=image_bytes) as resp:
                        resp_json = await resp.json()
                        return resp_json["vector"]
        raise ValueError("Failed to get image embedding after multiple retries.")

    async def create_embedding_for_text(self, q: str) -> list[float]:
        """Create an embedding vector for text (for image-text similarity).

        Args:
            q: Text query to embed

        Returns:
            Embedding vector as a list of floats

        Raises:
            ValueError: If embedding creation fails after retries
        """
        endpoint = urljoin(self.endpoint, "computervision/retrieval:vectorizeText")
        headers = {"Content-Type": "application/json"}
        params = {"api-version": "2024-02-01", "model-version": "2023-04-15"}
        data = {"text": q}
        headers["Authorization"] = "Bearer " + await self.token_provider()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=endpoint, params=params, headers=headers, json=data, raise_for_status=True
            ) as response:
                json = await response.json()
                return json["vector"]
        raise ValueError("Failed to get text embedding after multiple retries.")

    def before_retry_sleep(self, retry_state):  # noqa: ARG002
        """Log before sleeping on rate limit."""
        logger.info("Rate limited on the Vision embeddings API, sleeping before retrying...")
