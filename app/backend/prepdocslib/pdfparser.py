import html
import io
import logging
import uuid
from collections.abc import AsyncGenerator
from enum import Enum
from typing import IO, Optional

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
from PIL import Image
from pypdf import PdfReader

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


class DocumentAnalysisParser(Parser):
    """
    Concrete parser backed by Azure AI Document Intelligence that can parse many document formats into pages
    To learn more, please visit https://learn.microsoft.com/azure/ai-services/document-intelligence/overview
    """

    def __init__(
        self,
        endpoint: str,
        credential: AsyncTokenCredential | AzureKeyCredential,
        model_id: str = "prebuilt-layout",
        process_figures: bool = False,
    ) -> None:
        self.model_id = model_id
        self.endpoint = endpoint
        self.credential = credential
        self.process_figures = process_figures

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        logger.info("Extracting text from '%s' using Azure Document Intelligence", content.name)

        async with DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=self.credential
        ) as document_intelligence_client:
            # Always convert to bytes up front to avoid passing a FileStorage/stream object
            try:
                content.seek(0)
            except Exception:
                pass
            content_bytes = content.read()

            poller = None
            doc_for_pymupdf = None

            if self.process_figures:
                try:
                    poller = await document_intelligence_client.begin_analyze_document(
                        model_id="prebuilt-layout",
                        body=AnalyzeDocumentRequest(bytes_source=content_bytes),
                        output=["figures"],
                        features=["ocrHighResolution"],
                        output_content_format="markdown",
                    )
                    doc_for_pymupdf = pymupdf.open(stream=io.BytesIO(content_bytes))
                except HttpResponseError as e:
                    if e.error and e.error.code == "InvalidArgument":
                        logger.error(
                            "This document type does not support media description. Proceeding with standard analysis."
                        )
                    else:
                        logger.error(
                            "Unexpected error analyzing document for media description: %s. Proceeding with standard analysis.",
                            e,
                        )
                    poller = None

            if poller is None:
                poller = await document_intelligence_client.begin_analyze_document(
                    model_id=self.model_id,
                    body=AnalyzeDocumentRequest(bytes_source=content_bytes),
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
                if self.process_figures:
                    figures_on_page = [
                        figure
                        for figure in (analyze_result.figures or [])
                        if figure.bounding_regions and figure.bounding_regions[0].page_number == page.page_number
                    ]
                page_images: list[ImageOnPage] = []
                page_tables: list[str] = []

                class ObjectType(Enum):
                    NONE = -1
                    TABLE = 0
                    FIGURE = 1

                MaskEntry = tuple[ObjectType, Optional[int]]

                page_offset = page.spans[0].offset
                page_length = page.spans[0].length
                mask_chars: list[MaskEntry] = [(ObjectType.NONE, None)] * page_length
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
                added_objects: set[MaskEntry] = set()
                for idx, mask_char in enumerate(mask_chars):
                    object_type, object_idx = mask_char
                    if object_type == ObjectType.NONE:
                        page_text += analyze_result.content[page_offset + idx]
                    elif object_type == ObjectType.TABLE:
                        if object_idx is None:
                            raise ValueError("Expected object_idx to be set")
                        if mask_char not in added_objects:
                            table_html = DocumentAnalysisParser.table_to_html(tables_on_page[object_idx])
                            page_tables.append(table_html)
                            page_text += table_html
                            added_objects.add(mask_char)
                    elif object_type == ObjectType.FIGURE:
                        if object_idx is None:
                            raise ValueError("Expected object_idx to be set")
                        if doc_for_pymupdf is None:  # pragma: no cover
                            raise ValueError("Expected doc_for_pymupdf to be set for figure processing")
                        if mask_char not in added_objects:
                            image_on_page = await DocumentAnalysisParser.figure_to_image(
                                doc_for_pymupdf, figures_on_page[object_idx]
                            )
                            page_images.append(image_on_page)
                            page_text += image_on_page.placeholder
                            added_objects.add(mask_char)

                # We remove these comments since they are not needed and skew the page numbers
                page_text = page_text.replace("<!-- PageBreak -->", "")
                # We remove excess newlines at the beginning and end of the page
                page_text = page_text.strip()
                yield Page(
                    page_num=page.page_number - 1,
                    offset=offset,
                    text=page_text,
                    images=page_images,
                    tables=page_tables,
                )
                offset += len(page_text)

    @staticmethod
    async def figure_to_image(doc: pymupdf.Document, figure: DocumentFigure) -> ImageOnPage:
        figure_title = figure.caption.content if figure.caption and figure.caption.content else ""
        # Generate a random UUID if figure.id is None
        figure_id = figure.id or f"fig_{uuid.uuid4().hex[:8]}"
        figure_filename = f"figure{figure_id.replace('.', '_')}.png"
        logger.info("Cropping figure %s with title '%s'", figure_id, figure_title)
        placeholder = f'<figure id="{figure_id}"></figure>'
        if not figure.bounding_regions:
            return ImageOnPage(
                bytes=b"",
                page_num=0,  # 0-indexed
                figure_id=figure_id,
                bbox=(0, 0, 0, 0),
                filename=figure_filename,
                title=figure_title,
                placeholder=placeholder,
                mime_type="image/png",
            )
        if len(figure.bounding_regions) > 1:
            logger.warning("Figure %s has more than one bounding region, using the first one", figure_id)
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
        return ImageOnPage(
            bytes=cropped_img,
            page_num=page_number - 1,  # Convert to 0-indexed
            figure_id=figure_id,
            bbox=bbox_pixels,
            filename=figure_filename,
            title=figure_title,
            placeholder=placeholder,
            mime_type="image/png",
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
    ) -> tuple[bytes, tuple[float, float, float, float]]:
        """
        Crops a region from a given page in a PDF and returns it as an image.

        :param pdf_path: Path to the PDF file.
        :param page_number: The page number to crop from (0-indexed).
        :param bbox_inches: A tuple of (x0, y0, x1, y1) coordinates for the bounding box, in inches.
        :return: A tuple of (image_bytes, bbox_pixels).
        """
        # Scale the bounding box to 72 DPI
        bbox_dpi = 72
        # We multiply using unpacking to ensure the resulting tuple has the correct number of elements
        x0, y0, x1, y1 = (round(x * bbox_dpi, 2) for x in bbox_inches)
        bbox_pixels = (x0, y0, x1, y1)
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
