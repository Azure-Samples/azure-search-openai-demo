"""Shared ingestion helper functions for parser selection and setup.

These utilities allow both local scripts (prepdocs.py) and Azure Functions
(document_extractor) to reuse consistent logic for selecting parsers.
"""

from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential

from .htmlparser import LocalHTMLParser
from .parser import Parser
from .pdfparser import DocumentAnalysisParser, LocalPdfParser
from .textparser import TextParser


def select_parser(
    *,
    file_name: str,
    content_type: str,
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: str | None,
    document_intelligence_key: str | None = None,
    process_figures: bool = False,
    use_local_pdf_parser: bool = False,
    use_local_html_parser: bool = False,
) -> Parser:
    """Return a parser instance appropriate for the file type and configuration.

    Args:
        file_name: Source filename (used to derive extension)
        content_type: MIME type (fallback for extension-based selection)
        azure_credential: Token credential for DI service
        document_intelligence_service: Name of DI service (None disables DI)
        document_intelligence_key: Optional key credential (overrides token when provided)
        process_figures: Whether figure extraction should be enabled in DI parser
        use_local_pdf_parser: Force local PDF parsing instead of DI
        use_local_html_parser: Force local HTML parsing instead of DI

    Returns:
        Parser capable of yielding Page objects for the document.

    Raises:
        ValueError: Unsupported file type or missing DI configuration for required formats.
    """
    extension = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    ext_with_dot = f".{extension}" if extension else ""

    # Build DI parser lazily only if needed
    di_parser: DocumentAnalysisParser | None = None
    if document_intelligence_service:
        credential: AsyncTokenCredential | AzureKeyCredential
        if document_intelligence_key:
            credential = AzureKeyCredential(document_intelligence_key)
        else:
            credential = azure_credential
        di_parser = DocumentAnalysisParser(
            endpoint=f"https://{document_intelligence_service}.cognitiveservices.azure.com/",
            credential=credential,
            process_figures=process_figures,
        )

    # Plain text / structured text formats always local
    if ext_with_dot in {".txt", ".md", ".csv", ".json"} or content_type.startswith("text/plain"):
        return TextParser()

    # HTML
    if ext_with_dot in {".html", ".htm"} or content_type in {"text/html", "application/html"}:
        if use_local_html_parser or not di_parser:
            return LocalHTMLParser()
        return di_parser

    # PDF
    if ext_with_dot == ".pdf":
        if use_local_pdf_parser or not di_parser:
            return LocalPdfParser()
        return di_parser

    # Formats requiring DI
    di_required_exts = {".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".heic"}
    if ext_with_dot in di_required_exts:
        if not di_parser:
            raise ValueError("Document Intelligence service must be configured to process this file type")
        return di_parser

    # Fallback: if MIME suggests application/* and DI available, use DI
    if content_type.startswith("application/") and di_parser:
        return di_parser

    raise ValueError(f"Unsupported file type: {file_name}")
