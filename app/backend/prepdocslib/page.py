from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ImageOnPage:
    bytes: bytes
    bbox: tuple[float, float, float, float]  # Pixels
    filename: str
    description: str
    figure_id: str
    page_num: int  # 0-indexed
    url: Optional[str] = None
    embedding: Optional[list[float]] = None


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
