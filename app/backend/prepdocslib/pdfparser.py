import html
import io
import logging
from collections.abc import AsyncGenerator
from enum import Enum
from typing import IO, Optional, Union

import pymupdf
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    AnalyzeResult,
    DocumentFigure,
    DocumentTable,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import HttpResponseError
from openai import AsyncOpenAI
from PIL import Image
from pypdf import PdfReader

from .mediadescriber import (
    ContentUnderstandingDescriber,
    MediaDescriber,
    MultimodalModelDescriber,
)
from .page import ImageOnPage, Page
from .parser import Parser

logger = logging.getLogger("scripts")


class LocalPdfParser(Parser):
    """
    Concrete parser backed by PyPDF that can parse PDFs into pages
    To learn more, please visit https://pypi.org/project/pypdf/
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        logger.info("Extracting text from '%s' using local PDF parser (pypdf)", content.name)

        reader = PdfReader(content)
        pages = reader.pages
        offset = 0
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            yield Page(page_num=page_num, offset=offset, text=page_text)
            offset += len(page_text)


class MediaDescriptionStrategy(Enum):
    NONE = "none"
    OPENAI = "openai"
    CONTENTUNDERSTANDING = "content_understanding"


class DocumentAnalysisParser(Parser):
    """
    Concrete parser backed by Azure AI Document Intelligence that can parse many document formats into pages
    To learn more, please visit https://learn.microsoft.com/azure/ai-services/document-intelligence/overview
    """

    def __init__(
        self,
        endpoint: str,
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        model_id="prebuilt-layout",
        media_description_strategy: Enum = MediaDescriptionStrategy.NONE,
        # If using OpenAI, this is the client to use
        openai_client: Union[AsyncOpenAI, None] = None,
        openai_model: Optional[str] = None,
        openai_deployment: Optional[str] = None,
        # If using Content Understanding, this is the endpoint for the service
        content_understanding_endpoint: Union[str, None] = None,
        # should this take the blob storage info too?
    ):
        self.model_id = model_id
        self.endpoint = endpoint
        self.credential = credential
        self.media_description_strategy = media_description_strategy
        if media_description_strategy == MediaDescriptionStrategy.OPENAI:
            logger.info("Including media description with OpenAI")
            self.use_content_understanding = False
            self.openai_client = openai_client
            self.openai_model = openai_model
            self.openai_deployment = openai_deployment
        if media_description_strategy == MediaDescriptionStrategy.CONTENTUNDERSTANDING:
            logger.info("Including media description with Azure Content Understanding")
            self.content_understanding_endpoint = content_understanding_endpoint

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        logger.info("Extracting text from '%s' using Azure Document Intelligence", content.name)

        async with DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=self.credential
        ) as document_intelligence_client:
            file_analyzed = False

            media_describer: Union[ContentUnderstandingDescriber, MultimodalModelDescriber, None] = None
            if self.media_description_strategy == MediaDescriptionStrategy.CONTENTUNDERSTANDING:
                if self.content_understanding_endpoint is None:
                    raise ValueError(
                        "Content Understanding endpoint must be provided when using Content Understanding strategy"
                    )
                if isinstance(self.credential, AzureKeyCredential):
                    raise ValueError(
                        "AzureKeyCredential is not supported for Content Understanding, use keyless auth instead"
                    )
                media_describer = ContentUnderstandingDescriber(self.content_understanding_endpoint, self.credential)

            if self.media_description_strategy == MediaDescriptionStrategy.OPENAI:
                if self.openai_client is None or self.openai_model is None:
                    raise ValueError("OpenAI client must be provided when using OpenAI media description strategy")
                media_describer = MultimodalModelDescriber(
                    self.openai_client, self.openai_model, self.openai_deployment
                )

            if media_describer is not None:
                content_bytes = content.read()
                try:
                    poller = await document_intelligence_client.begin_analyze_document(
                        model_id="prebuilt-layout",
                        analyze_request=AnalyzeDocumentRequest(bytes_source=content_bytes),
                        output=["figures"],
                        features=["ocrHighResolution"],
                        output_content_format="markdown",
                    )
                    doc_for_pymupdf = pymupdf.open(stream=io.BytesIO(content_bytes))
                    file_analyzed = True
                except HttpResponseError as e:
                    content.seek(0)
                    if e.error and e.error.code == "InvalidArgument":
                        logger.error(
                            "This document type does not support media description. Proceeding with standard analysis."
                        )
                    else:
                        logger.error(
                            "Unexpected error analyzing document for media description: %s. Proceeding with standard analysis.",
                            e,
                        )

            if file_analyzed is False:
                poller = await document_intelligence_client.begin_analyze_document(
                    model_id=self.model_id, analyze_request=content, content_type="application/octet-stream"
                )
            analyze_result: AnalyzeResult = await poller.result()

            offset = 0

            for page in analyze_result.pages:
                tables_on_page = [
                    table
                    for table in (analyze_result.tables or [])
                    if table.bounding_regions and table.bounding_regions[0].page_number == page.page_number
                ]
                figures_on_page = []
                if self.media_description_strategy != MediaDescriptionStrategy.NONE:
                    figures_on_page = [
                        figure
                        for figure in (analyze_result.figures or [])
                        if figure.bounding_regions and figure.bounding_regions[0].page_number == page.page_number
                    ]
                page_images: list[ImageOnPage] = []

                class ObjectType(Enum):
                    NONE = -1
                    TABLE = 0
                    FIGURE = 1

                page_offset = page.spans[0].offset
                page_length = page.spans[0].length
                mask_chars: list[tuple[ObjectType, Union[int, None]]] = [(ObjectType.NONE, None)] * page_length
                # mark all positions of the table spans in the page
                for table_idx, table in enumerate(tables_on_page):
                    for span in table.spans:
                        # replace all table spans with "table_id" in table_chars array
                        for i in range(span.length):
                            idx = span.offset - page_offset + i
                            if idx >= 0 and idx < page_length:
                                mask_chars[idx] = (ObjectType.TABLE, table_idx)
                # mark all positions of the figure spans in the page
                for figure_idx, figure in enumerate(figures_on_page):
                    for span in figure.spans:
                        # replace all figure spans with "figure_id" in figure_chars array
                        for i in range(span.length):
                            idx = span.offset - page_offset + i
                            if idx >= 0 and idx < page_length:
                                mask_chars[idx] = (ObjectType.FIGURE, figure_idx)

                # build page text by replacing characters in table spans with table html
                page_text = ""
                added_objects = set()  # set of object types todo mypy
                for idx, mask_char in enumerate(mask_chars):
                    object_type, object_idx = mask_char
                    if object_type == ObjectType.NONE:
                        page_text += analyze_result.content[page_offset + idx]
                    elif object_type == ObjectType.TABLE:
                        if object_idx is None:
                            raise ValueError("Expected object_idx to be set")
                        if mask_char not in added_objects:
                            page_text += DocumentAnalysisParser.table_to_html(tables_on_page[object_idx])
                            added_objects.add(mask_char)
                    elif object_type == ObjectType.FIGURE:
                        if media_describer is None:
                            raise ValueError("media_describer should not be None, unable to describe figure")
                        if object_idx is None:
                            raise ValueError("Expected object_idx to be set")
                        if mask_char not in added_objects:
                            image_on_page = await DocumentAnalysisParser.process_figure(
                                doc_for_pymupdf, figures_on_page[object_idx], media_describer
                            )
                            page_images.append(image_on_page)
                            page_text += image_on_page.description
                            added_objects.add(mask_char)
                # We remove these comments since they are not needed and skew the page numbers
                page_text = page_text.replace("<!-- PageBreak -->", "")
                # We remove excess newlines at the beginning and end of the page
                page_text = page_text.strip()
                yield Page(page_num=page.page_number - 1, offset=offset, text=page_text, images=page_images)
                offset += len(page_text)

    @staticmethod
    async def process_figure(doc: pymupdf.Document, figure: DocumentFigure, media_describer: MediaDescriber) -> str:
        figure_title = (figure.caption and figure.caption.content) or ""
        logger.info(
            "Describing figure %s with title '%s' using %s", figure.id, figure_title, type(media_describer).__name__
        )
        if not figure.bounding_regions:
            return f"<figure><figcaption>{figure_title}</figcaption></figure>"
        if len(figure.bounding_regions) > 1:
            logger.warning("Figure %s has more than one bounding region, using the first one", figure.id)
        first_region = figure.bounding_regions[0]
        # To learn more about bounding regions, see https://aka.ms/bounding-region
        bounding_box = (
            first_region.polygon[0],  # x0 (left)
            first_region.polygon[1],  # y0 (top
            first_region.polygon[4],  # x1 (right)
            first_region.polygon[5],  # y1 (bottom)
        )
        page_number = first_region["pageNumber"]  # 1-indexed
        cropped_img, bbox_pixels = DocumentAnalysisParser.crop_image_from_pdf_page(doc, page_number - 1, bounding_box)
        figure_description = await media_describer.describe_image(cropped_img)
        return ImageOnPage(
            bytes=cropped_img,
            page_num=page_number,
            figure_id=figure.id,
            bbox=bbox_pixels,
            filename=f"figure{figure.id.replace(".", "_")}.png",
            description=f"<figure><figcaption>{figure_title}<br>{figure_description}</figcaption></figure>",
        )

    @staticmethod
    def table_to_html(table: DocumentTable):
        table_html = "<figure><table>"
        rows = [
            sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index)
            for i in range(table.row_count)
        ]
        for row_cells in rows:
            table_html += "<tr>"
            for cell in row_cells:
                tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
                cell_spans = ""
                if cell.column_span is not None and cell.column_span > 1:
                    cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span is not None and cell.row_span > 1:
                    cell_spans += f" rowSpan={cell.row_span}"
                table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            table_html += "</tr>"
        table_html += "</table></figure>"
        return table_html

    @staticmethod
    def crop_image_from_pdf_page(
        doc: pymupdf.Document, page_number: int, bbox_inches: tuple[float, float, float, float]
    ) -> tuple[bytes, list[float]]:
        """
        Crops a region from a given page in a PDF and returns it as an image.

        :param pdf_path: Path to the PDF file.
        :param page_number: The page number to crop from (0-indexed).
        :param bbox_inches: A tuple of (x0, y0, x1, y1) coordinates for the bounding box, in inches.
        :return: A PIL Image of the cropped area.
        """
        # Scale the bounding box to 72 DPI
        bbox_dpi = 72
        bbox_pixels = [x * bbox_dpi for x in bbox_inches]
        rect = pymupdf.Rect(bbox_pixels)
        # Assume that the PDF has 300 DPI,
        # and use the matrix to convert between the 2 DPIs
        page_dpi = 300
        page = doc.load_page(page_number)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(page_dpi / bbox_dpi, page_dpi / bbox_dpi), clip=rect)

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        bytes_io = io.BytesIO()
        img.save(bytes_io, format="PNG")
        return bytes_io.getvalue(), bbox_pixels
