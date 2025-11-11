"""Utilities for describing and enriching figures extracted from documents."""

import logging
from enum import Enum
from typing import Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential

from .blobmanager import BaseBlobManager
from .embeddings import ImageEmbeddings
from .mediadescriber import (
    ContentUnderstandingDescriber,
    MediaDescriber,
    MultimodalModelDescriber,
)
from .page import ImageOnPage

logger = logging.getLogger("scripts")


class MediaDescriptionStrategy(Enum):
    """Supported mechanisms for describing images extracted from documents."""

    NONE = "none"
    OPENAI = "openai"
    CONTENTUNDERSTANDING = "content_understanding"


class FigureProcessor:
    """Helper that lazily creates a media describer and captions figures on demand."""

    def __init__(
        self,
        *,
        credential: AsyncTokenCredential | AzureKeyCredential | None = None,
        strategy: MediaDescriptionStrategy = MediaDescriptionStrategy.NONE,
        openai_client: Any | None = None,
        openai_model: str | None = None,
        openai_deployment: str | None = None,
        content_understanding_endpoint: str | None = None,
    ) -> None:
        self.credential = credential
        self.strategy = strategy
        self.openai_client = openai_client
        self.openai_model = openai_model
        self.openai_deployment = openai_deployment
        self.content_understanding_endpoint = content_understanding_endpoint
        self.media_describer: MediaDescriber | None = None
        self.content_understanding_ready = False

    async def get_media_describer(self) -> MediaDescriber | None:
        """Return (and lazily create) the media describer for this processor."""

        if self.strategy == MediaDescriptionStrategy.NONE:
            return None

        if self.media_describer is not None:
            return self.media_describer

        if self.strategy == MediaDescriptionStrategy.CONTENTUNDERSTANDING:
            if self.content_understanding_endpoint is None:
                raise ValueError("Content Understanding strategy requires an endpoint")
            if self.credential is None:
                raise ValueError("Content Understanding strategy requires a credential")
            if isinstance(self.credential, AzureKeyCredential):
                raise ValueError(
                    "Content Understanding does not support key credentials; provide a token credential instead"
                )
            self.media_describer = ContentUnderstandingDescriber(self.content_understanding_endpoint, self.credential)
            return self.media_describer

        if self.strategy == MediaDescriptionStrategy.OPENAI:
            if self.openai_client is None or self.openai_model is None:
                raise ValueError("OpenAI strategy requires both a client and a model name")
            self.media_describer = MultimodalModelDescriber(
                self.openai_client, model=self.openai_model, deployment=self.openai_deployment
            )
            return self.media_describer

        logger.warning("Unknown media description strategy '%s'; skipping description", self.strategy)
        return None

    def mark_content_understanding_ready(self) -> None:
        """Record that the Content Understanding analyzer exists to avoid recreating it."""

        self.content_understanding_ready = True

    async def describe(self, image_bytes: bytes) -> str | None:
        """Generate a description for the provided image bytes if a describer is available."""

        describer = await self.get_media_describer()
        if describer is None:
            return None
        if isinstance(describer, ContentUnderstandingDescriber) and not self.content_understanding_ready:
            await describer.create_analyzer()
            self.content_understanding_ready = True
        return await describer.describe_image(image_bytes)


def build_figure_markup(image: "ImageOnPage", description: Optional[str] = None) -> str:
    """Create consistent HTML markup for a figure description on demand."""

    caption_parts = [image.figure_id]
    if image.title:
        caption_parts.append(image.title)
    caption = " ".join(part for part in caption_parts if part)
    if description:
        return f"<figure><figcaption>{caption}<br>{description}</figcaption></figure>"
    return f"<figure><figcaption>{caption}</figcaption></figure>"


async def process_page_image(
    *,
    image: "ImageOnPage",
    document_filename: str,
    blob_manager: Optional[BaseBlobManager],
    image_embeddings_client: Optional[ImageEmbeddings],
    figure_processor: Optional[FigureProcessor] = None,
    user_oid: Optional[str] = None,
) -> "ImageOnPage":
    """Generate description, upload image, and optionally compute embedding for a figure."""

    if blob_manager is None:
        raise ValueError("BlobManager must be provided to process images.")

    # Generate plain (model) description text only; do not wrap in HTML markup here.
    description_text: str | None = None
    if figure_processor is not None:
        description_text = await figure_processor.describe(image.bytes)

    # Store plain descriptive text (can be None). HTML rendering is deferred to build_figure_markup.
    image.description = description_text

    if image.url is None:
        image.url = await blob_manager.upload_document_image(
            document_filename, image.bytes, image.filename, image.page_num, user_oid=user_oid
        )

    if image_embeddings_client is not None:
        try:
            image.embedding = await image_embeddings_client.create_embedding_for_image(image.bytes)
        except Exception:  # pragma: no cover - embedding failures shouldn't abort figure processing
            logger.warning("Image embedding generation failed for figure %s", image.figure_id, exc_info=True)

    return image
