"""
Data models for document ingestion.

This module contains the core data classes used throughout the ingestion pipeline.
"""

import base64
import os
import re
from dataclasses import dataclass, field
from typing import IO, Optional


class File:
    """
    Represents a file stored either locally or in a data lake storage account.
    This file might contain access control information about which users or groups can access it.

    Attributes:
        content: File-like object containing the file data
        acls: Access control lists (oids and groups)
        url: URL of the file in storage (set after upload)
    """

    def __init__(self, content: IO, acls: Optional[dict[str, list]] = None, url: Optional[str] = None):
        self.content = content
        self.acls = acls or {}
        self.url = url

    def filename(self) -> str:
        """
        Get the filename from the content object.

        Different file-like objects store the filename in different attributes:
        - File objects from open() have a .name attribute
        - HTTP uploaded files (werkzeug.datastructures.FileStorage) have a .filename attribute

        Returns:
            str: The basename of the file

        Raises:
            ValueError: If the content object has no filename attribute
        """
        content_name = None

        # Try to get filename attribute (common for HTTP uploaded files)
        if hasattr(self.content, "filename"):
            content_name = getattr(self.content, "filename")
            if content_name:
                return os.path.basename(content_name)

        # Try to get name attribute (common for file objects from open())
        if hasattr(self.content, "name"):
            content_name = getattr(self.content, "name")
            if content_name and content_name != "file":
                return os.path.basename(content_name)

        raise ValueError("The content object does not have a filename or name attribute.")

    def file_extension(self) -> str:
        """Get the file extension including the dot."""
        return os.path.splitext(self.filename())[1]

    def filename_to_id(self) -> str:
        """Generate a unique ID from the filename and ACLs."""
        filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", self.filename())
        filename_hash = base64.b16encode(self.filename().encode("utf-8")).decode("ascii")
        acls_hash = ""
        if self.acls:
            acls_hash = base64.b16encode(str(self.acls).encode("utf-8")).decode("ascii")
        return f"file-{filename_ascii}-{filename_hash}{acls_hash}"

    def close(self):
        """Close the file content."""
        if self.content:
            self.content.close()


@dataclass
class ImageOnPage:
    """Represents an image/figure extracted from a document page.

    Attributes:
        bytes: Raw image bytes
        page_num: 0-indexed page number where the image appears
        figure_id: Unique identifier for the figure
        bbox: Bounding box coordinates (x0, y0, x1, y1)
        filename: Generated filename for the image
        title: Caption or title of the figure
        placeholder: HTML placeholder to insert in text
        mime_type: MIME type of the image
        description: AI-generated description of the image
        url: URL after upload to storage
        embedding: Image embedding vector
    """

    bytes: bytes
    page_num: int
    figure_id: str
    bbox: tuple[float, float, float, float]
    filename: str
    title: str = ""
    placeholder: str = ""
    mime_type: str = "image/png"
    description: Optional[str] = None
    url: Optional[str] = None
    embedding: Optional[list[float]] = None

    def to_skill_payload(
        self,
        file_name: str,
        *,
        include_bytes_base64: bool = True,
    ) -> dict:
        """Convert to a payload suitable for Azure AI Search skills.

        Args:
            file_name: The source document filename
            include_bytes_base64: Whether to include base64-encoded image bytes

        Returns:
            Dictionary payload for skill processing
        """
        from dataclasses import asdict
        data = asdict(self)
        data.pop("bytes", None)

        if include_bytes_base64:
            b = self.bytes if isinstance(self.bytes, (bytes, bytearray)) else b""
            data["bytes_base64"] = base64.b64encode(b).decode("utf-8")

        data["document_file_name"] = file_name
        return data

    @classmethod
    def from_skill_payload(cls, data: dict) -> tuple["ImageOnPage", str]:
        """Create an ImageOnPage from a skill payload.

        Args:
            data: Dictionary payload from skill processing

        Returns:
            Tuple of (ImageOnPage, document_file_name)
        """
        bytes_base64 = data.get("bytes_base64")
        if bytes_base64:
            try:
                raw_bytes = base64.b64decode(bytes_base64)
            except Exception as exc:
                raise ValueError("Invalid bytes_base64 image data") from exc
        else:
            raw_bytes = b""

        try:
            page_num = int(data.get("page_num") or 0)
        except Exception:
            page_num = 0

        bbox_val = data.get("bbox")
        if isinstance(bbox_val, list) and len(bbox_val) == 4:
            bbox = tuple(bbox_val)
        else:
            bbox = (0, 0, 0, 0)

        filename = data.get("filename")
        figure_id = data.get("figure_id")
        placeholder = data.get("placeholder")
        if filename is None:
            raise ValueError("filename is required")
        if figure_id is None:
            raise ValueError("figure_id is required for ImageOnPage deserialization")

        if placeholder is None:
            placeholder = f'<figure id="{figure_id}"></figure>'

        image = cls(
            bytes=raw_bytes,
            bbox=bbox,
            page_num=page_num,
            filename=filename,
            figure_id=figure_id,
            placeholder=placeholder,
            mime_type=data.get("mime_type") or "image/png",
            title=data.get("title") or "",
            description=data.get("description"),
            url=data.get("url"),
        )
        return image, data.get("document_file_name", "")


@dataclass
class Page:
    """Represents a parsed page from a document.

    Attributes:
        page_num: 0-indexed page number
        offset: Character offset from the start of the document
        text: Extracted text content
        images: List of images found on this page
        tables: List of HTML table representations
    """

    page_num: int
    offset: int
    text: str
    images: list[ImageOnPage] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    """Represents a text chunk after splitting.

    Attributes:
        text: The chunk text content
        page_num: Page number where this chunk starts
        images: Images associated with this chunk
    """

    text: str
    page_num: int
    images: list[ImageOnPage] = field(default_factory=list)


@dataclass
class Section:
    """
    A section of a page that is stored in a search service.
    These sections are used as context by Azure OpenAI service.

    Attributes:
        chunk: The text chunk containing the content
        content: The source file information
        category: Optional category for filtering
    """

    chunk: Chunk
    content: File
    category: Optional[str] = None
