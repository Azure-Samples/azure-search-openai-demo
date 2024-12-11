import html
import logging
from typing import IO, AsyncGenerator, Union

from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentTable
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from pypdf import PdfReader
from .listfilestrategy import File
from prepdocslib.blobmanager import BlobManager
import pickle
import json
import os
import sys

from .page import Page
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
        self, endpoint: str, credential: Union[AsyncTokenCredential, AzureKeyCredential], model_id="prebuilt-layout",
        blob_manager_interim_files: BlobManager=None,
    ):
        self.model_id = model_id
        self.endpoint = endpoint
        self.credential = credential
        self.blob_manager_interim_files = blob_manager_interim_files
        self.cache_dir = "./data_interim/"
        if not os.path.exists(self.cache_dir ):
            os.makedirs(self.cache_dir )

    async def cache_doc_intelligence_results(self, form_recognizer_results, content_name):
        """
        Save Document intelligence to blob as JSON and pickle
        """
        content_name = content_name.split("/")[-1]
        base_name = f"{self.cache_dir}{content_name}"
        pkl_file = f"{base_name}.doc_intel_obj.pkl"
        json_file = f"{base_name}.doc_intel_dict.json"
        with open(json_file, "w") as f:
            form_recognizer_results_dict = form_recognizer_results.as_dict()
            f.write(json.dumps(form_recognizer_results_dict, indent=4))
        with open(pkl_file, "wb") as file:
            pickle.dump(form_recognizer_results, file)
        print("Saving interim files")
        for filename in [pkl_file, json_file]:
            file = File(content=open(filename, mode="rb"))
            blob_sas_uris = await self.blob_manager_interim_files.upload_blob(file)
            # Remove file to save space
            os.remove(filename)
        
    async def check_interim_files(self, base_name):
        """
        Avoid reprocessing files that have already been processed
        """
        pkl_file = f"{base_name}.doc_intel_obj.pkl"
        pkl_file = pkl_file.split("/")[-1]
        files = await self.blob_manager_interim_files.list_paths()
        for filename in files:
            if pkl_file in filename:
                content = await self.blob_manager_interim_files.download_blob(filename)
                os.remove(f"{self.cache_dir}/{pkl_file}")
                return content

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        
        async with DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=self.credential
        ) as document_intelligence_client:
            
            # mjh Load results from blob file if it exists
            form_recognizer_results = await self.check_interim_files(content.name)

            if form_recognizer_results is None:
                logger.info("Extracting text from '%s' using Azure Document Intelligence", content.name)
                poller = await document_intelligence_client.begin_analyze_document(
                    model_id=self.model_id, 
                    analyze_request=content, 
                    content_type="application/octet-stream",
                )
                form_recognizer_results = await poller.result()

                # mjh
                await self.cache_doc_intelligence_results(form_recognizer_results, content.name)
            else:
                logger.info("Extracting text from '%s' using previously parsed results", content.name)

            # mjh Converted to use JSON rather than object, so we cache results
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

    @classmethod
    def table_to_html(cls, table: DocumentTable):
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
