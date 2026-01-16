import base64
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ImageOnPage:
    bytes: bytes
    bbox: tuple[float, float, float, float]  # Pixels
    filename: str
    figure_id: str
    page_num: int  # 0-indexed
    placeholder: str  # HTML placeholder in page text, e.g. '<figure id="fig_..."></figure>'
    mime_type: str = "image/png"  # Set by parser; default assumes PNG rendering
    url: Optional[str] = None
    title: str = ""
    embedding: Optional[list[float]] = None
    description: Optional[str] = None

    def to_skill_payload(
        self,
        file_name: str,
        *,
        include_bytes_base64: bool = True,
    ) -> dict[str, Any]:
        data = asdict(self)

        # Remove raw bytes to keep payload lean (and JSON-friendly without extra handling).
        data.pop("bytes", None)

        # Optionally include base64-encoded bytes for skills that need it
        if include_bytes_base64:
            b = self.bytes if isinstance(self.bytes, (bytes, bytearray)) else b""
            data["bytes_base64"] = base64.b64encode(b).decode("utf-8")

        data["document_file_name"] = file_name
        return data

    @classmethod
    def from_skill_payload(cls, data: dict[str, Any]) -> tuple["ImageOnPage", str]:
        # Decode base64 image data (optional - may be omitted if already persisted to blob)
        bytes_base64 = data.get("bytes_base64")
        if bytes_base64:
            try:
                raw_bytes = base64.b64decode(bytes_base64)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError("Invalid bytes_base64 image data") from exc
        else:
            raw_bytes = b""  # Empty bytes if not provided (already uploaded to blob)

        # page_num may arrive as str; coerce
        try:
            page_num = int(data.get("page_num") or 0)
        except Exception:
            page_num = 0

        # bbox may arrive as list; coerce into tuple
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

        # Generate placeholder if not provided
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
    """
    A single page from a document

    Attributes:
        page_num (int): Page number (0-indexed)
        offset (int): If the text of the entire Document was concatenated into a single string, the index of the first character on the page. For example, if page 1 had the text "hello" and page 2 had the text "world", the offset of page 2 is 5 ("hellow")
        text (str): The text of the page
    """

    page_num: int
    offset: int
    text: str
    images: list[ImageOnPage] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    """Semantic chunk emitted by the splitter (may originate wholly within one page
    or be the result of a cross-page merge / trailing fragment carry-forward).

    Attributes:
        page_num (int): Logical source page number (0-indexed) for the originating
            portion of content. For merged content spanning pages we keep the earliest
            contributing page number for stable attribution.
        text (str): Textual content of the chunk.
        images (list[ImageOnPage]): Images associated with this chunk, if any.
    """

    page_num: int
    text: str
    images: list[ImageOnPage] = field(default_factory=list)
