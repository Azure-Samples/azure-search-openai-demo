from dataclasses import dataclass, field


@dataclass
class ImageOnPage:
    bytes: bytes
    bbox: list[float, float, float, float]  # Pixels
    filename: str
    description: str
    figure_id: str
    page_num: int  # 0-indexed
    url: str | None = None
    embedding: list[float] | None = None


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
class SplitPage:
    """
    A section of a page that has been split into a smaller chunk.

    Attributes:
        page_num (int): Page number (0-indexed)
        text (str): The text of the section
    """

    page_num: int
    text: str
    images: list[ImageOnPage] = field(default_factory=list)
