import html
import io
import logging
import os
from typing import IO, AsyncGenerator, Union

import pymupdf
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.ai.documentintelligence.models import DocumentTable
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from PIL import Image
from pypdf import PdfReader

from .page import Page
from .parser import Parser
from .cu_image import ContentUnderstandingManager

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
        credential: Union[AsyncTokenCredential, AzureKeyCredential],
        model_id="prebuilt-layout",
        use_content_understanding=True,
        content_understanding_endpoint: str = None,
    ):
        self.model_id = model_id
        self.endpoint = endpoint
        self.credential = credential
        self.use_content_understanding = use_content_understanding
        self.content_understanding_endpoint = content_understanding_endpoint

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        logger.info("Extracting text from '%s' using Azure Document Intelligence", content.name)

        cu_manager = ContentUnderstandingManager(self.content_understanding_endpoint, self.credential)
        async with DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=self.credential
        ) as document_intelligence_client:
            # turn content into bytes
            content_bytes = content.read()
            if self.use_content_understanding:
                poller = await document_intelligence_client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    analyze_request=AnalyzeDocumentRequest(bytes_source=content_bytes),
                    # content_type="application/octet-stream",
                    output=["figures"],
                    features=["ocrHighResolution"],
                    output_content_format="markdown",
                )
            else:
                poller = await document_intelligence_client.begin_analyze_document(
                    model_id=self.model_id, analyze_request=content, content_type="application/octet-stream"
                )
            form_recognizer_results = await poller.result()

            offset = 0
            for page_num, page in enumerate(form_recognizer_results.pages):
                tables_on_page = [
                    table
                    for table in (form_recognizer_results.tables or [])
                    if table.bounding_regions and table.bounding_regions[0].page_number == page_num + 1
                ]

                # mark all positions of the table spans in the page
                page_offset = page.spans[0].offset
                page_length = page.spans[0].length
                table_chars = [-1] * page_length
                for table_id, table in enumerate(tables_on_page):
                    for span in table.spans:
                        # replace all table spans with "table_id" in table_chars array
                        for i in range(span.length):
                            idx = span.offset - page_offset + i
                            if idx >= 0 and idx < page_length:
                                table_chars[idx] = table_id

                # build page text by replacing characters in table spans with table html
                page_text = ""
                added_tables = set()
                for idx, table_id in enumerate(table_chars):
                    if table_id == -1:
                        page_text += form_recognizer_results.content[page_offset + idx]
                    elif table_id not in added_tables:
                        page_text += DocumentAnalysisParser.table_to_html(tables_on_page[table_id])
                        added_tables.add(table_id)

                yield Page(page_num=page_num, offset=offset, text=page_text)
                offset += len(page_text)

            figure_results = {}
            if form_recognizer_results.figures:
                doc = pymupdf.open(stream=io.BytesIO(content_bytes))
                for figures_idx, figure in enumerate(form_recognizer_results.figures):
                    for region in figure.bounding_regions:
                        print(f"\tFigure body bounding regions: {region}")
                        # To learn more about bounding regions, see https://aka.ms/bounding-region
                        bounding_box = (
                            region.polygon[0],  # x0 (left)
                            region.polygon[1],  # y0 (top
                            region.polygon[4],  # x1 (right)
                            region.polygon[5],  # y1 (bottom)
                        )
                    page_number = figure.bounding_regions[0]["pageNumber"]
                    cropped_img = DocumentAnalysisParser.crop_image_from_pdf_page(doc, page_number - 1, bounding_box)

                    # Save the figure
                    bytes_io = io.BytesIO()
                    cropped_img.save(bytes_io, format="PNG")
                    image_fields = await cu_manager.run_cu_image(bytes_io.getvalue())
                    figure_results[figure.id] = image_fields

        md_content = analyze_result.content
        page_to_figure = {}
        for figure in analyze_result.figures:
            # Parse figure id
            # https://learn.microsoft.com/azure/ai-services/document-intelligence/concept/analyze-document-response?view=doc-intel-4.0.0#figures
            figure_id = figure.id.split(".")  # 3.1 where 3 is the page number and 1 is the figure number, 1-indexed
            page = int(figure_id[0])
            if page not in page_to_figure:
                page_to_figure[page] = []
            page_to_figure[page].append(figure.id)
        for page in form_recognizer_results.pages:
            # Use the text span to extract the markdown on the page
            span = page.spans[0]
            page_md_content = md_content[span.offset : span.offset + span.length]
            if page.page_number in page_to_figure:
                page_figures = page_to_figure[page.page_number]
                # split the content on the figure tag
                parts = page_md_content.split("\n<figure>\n")
                for i, figure_id in enumerate(page_figures):
                    with open(
                        os.path.join(figures_directory, f"figure_imagecrop_{figure_id}_verbalized.json"), "r"
                    ) as f:
                        figure_content = json.dumps(json.load(f)["result"]["contents"][0])
                        parts[i] = parts[i] + f'<!-- FigureContent="{figure_content}" -->'
                    page_md_content = "\n".join(parts)
            with open(os.path.join(pages_md_directory, f"page_{page.page_number}.md"), "w", encoding="utf-8") as f:
                f.write(page_md_content)

    @staticmethod
    def table_to_html(table: DocumentTable):
        table_html = "<table>"
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
        table_html += "</table>"
        return table_html

    @staticmethod
    def crop_image_from_pdf_page(doc: pymupdf.Document, page_number, bounding_box):
        """
        Crops a region from a given page in a PDF and returns it as an image.

        :param pdf_path: Path to the PDF file.
        :param page_number: The page number to crop from (0-indexed).
        :param bounding_box: A tuple of (x0, y0, x1, y1) coordinates for the bounding box.
        :return: A PIL Image of the cropped area.
        """
        logger.info(f"Cropping image from PDF page {page_number} with bounding box {bounding_box}")
        page = doc.load_page(page_number)

        # Cropping the page. The rect requires the coordinates in the format (x0, y0, x1, y1).
        bbx = [x * 72 for x in bounding_box]
        rect = pymupdf.Rect(bbx)
        # 72 is the DPI ? what? explain this from CU
        pix = page.get_pixmap(matrix=pymupdf.Matrix(300 / 72, 300 / 72), clip=rect)

        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
