"""Utilities for processing document text and combining it with figure descriptions."""

import logging

from .figureprocessor import build_figure_markup
from .listfilestrategy import File
from .page import Page
from .searchmanager import Section
from .textsplitter import TextSplitter

logger = logging.getLogger("scripts")


def combine_text_with_figures(page: "Page") -> None:
    """Replace figure placeholders in page text with full description markup."""
    for image in page.images:
        if image.description and image.placeholder in page.text:
            figure_markup = build_figure_markup(image, image.description)
            page.text = page.text.replace(image.placeholder, figure_markup)
            logger.info("Replaced placeholder for figure %s with description markup", image.figure_id)
        elif not image.description:
            logger.debug("No description for figure %s; keeping placeholder", image.figure_id)
        elif image.placeholder not in page.text:
            logger.warning("Placeholder not found for figure %s in page %d", image.figure_id, page.page_num)


def process_text(
    pages: list["Page"],
    file: "File",
    splitter: "TextSplitter",
    category: str | None = None,
) -> list["Section"]:
    """Process document text and figures into searchable sections.
    Combines text with figure descriptions, splits into chunks, and
    associates figures with their containing sections.
    """
    # Step 1: Combine text with figures on each page
    for page in pages:
        combine_text_with_figures(page)

    # Step 2: Split combined text into chunks
    logger.info("Splitting '%s' into sections", file.filename())
    sections = [Section(chunk, content=file, category=category) for chunk in splitter.split_pages(pages)]

    # Step 3: Add images back to each section based on page number
    for section in sections:
        section.chunk.images = [
            image for page in pages if page.page_num == section.chunk.page_num for image in page.images
        ]

    return sections
