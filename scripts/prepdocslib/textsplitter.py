from abc import ABC
from typing import Generator, List

import tiktoken

from .page import Page, SplitPage


class TextSplitter(ABC):
    """
    Splits a list of pages into smaller chunks
    :param pages: The pages to split
    :return: A generator of SplitPage
    """

    def split_pages(self, pages: List[Page]) -> Generator[SplitPage, None, None]:
        if False:
            yield  # pragma: no cover - this is necessary for mypy to type check


STANDARD_LINE_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
CJK_LINE_BREAKS = [
    "。",
    "、",
    "，",
    "；",
    "：",
    "（",
    "）",
    "【",
    "】",
    "「",
    "」",
    "『",
    "』",
    "〔",
    "〕",
    "〈",
    "〉",
    "《",
    "》",
    "〖",
    "〗",
    "〘",
    "〙",
    "〚",
    "〛",
    "〝",
    "〞",
    "〟",
    "〰",
    "〾",
    "〿",
    "–",
    "—",
    "‘",
    "’",
    "‚",
    "‛",
    "“",
    "”",
    "„",
    "‟",
    "‹",
    "›",
    "‽",
    "⁇",
    "⁈",
    "⁉",
    "⸮",
    "ⸯ",
    "。",
    "々",
    "〻",
    "〼",
]
cl100k = tiktoken.get_encoding("cl100k_base")


def split_page_by_max_tokens(page_num: int, text: str, max_tokens: int) -> Generator[SplitPage, None, None]:
    """
    Splits page by tokens
    """
    tokens = cl100k.encode(text)
    if len(tokens) < max_tokens:
        yield SplitPage(page_num=page_num, text=text)
    else:
        # Split page in half and call function again
        # Overlap first and second halves by 5%
        first_half = text[: int(len(text) // 2.05)]
        second_half = text[int(len(text) // 1.95) :]
        yield from split_page_by_max_tokens(page_num, first_half, max_tokens)
        yield from split_page_by_max_tokens(page_num, second_half, max_tokens)


class SentenceTextSplitter(TextSplitter):
    """
    Class that splits pages into smaller chunks. This is required because embedding models may not be able to analyze an entire page at once
    """

    def __init__(self, has_image_embeddings: bool, verbose: bool = False, max_tokens_per_section: int = 500):
        self.sentence_endings = [".", "!", "?"] + ["。", "！", "？"]
        self.word_breaks = STANDARD_LINE_BREAKS + CJK_LINE_BREAKS
        self.max_section_length = 1000
        self.sentence_search_limit = 100
        self.max_tokens_per_section = max_tokens_per_section
        self.section_overlap = 100
        self.verbose = verbose
        self.has_image_embeddings = has_image_embeddings

    def split_pages(self, pages: List[Page]) -> Generator[SplitPage, None, None]:
        # Chunking is disabled when using GPT4V. To be updated in the future.
        if self.has_image_embeddings:
            for i, page in enumerate(pages):
                yield SplitPage(page_num=i, text=page.text)

        def find_page(offset):
            num_pages = len(pages)
            for i in range(num_pages - 1):
                if offset >= pages[i].offset and offset < pages[i + 1].offset:
                    return pages[i].page_num
            return pages[num_pages - 1].page_num

        all_text = "".join(page.text for page in pages)
        if len(all_text.strip()) == 0:
            return

        length = len(all_text)
        if length <= self.max_section_length:
            yield from split_page_by_max_tokens(
                page_num=find_page(0), text=all_text, max_tokens=self.max_tokens_per_section
            )
            return

        start = 0
        end = length
        while start + self.section_overlap < length:
            last_word = -1
            end = start + self.max_section_length

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while (
                    end < length
                    and (end - start - self.max_section_length) < self.sentence_search_limit
                    and all_text[end] not in self.sentence_endings
                ):
                    if all_text[end] in self.word_breaks:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in self.sentence_endings and last_word > 0:
                    end = last_word  # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while (
                start > 0
                and start > end - self.max_section_length - 2 * self.sentence_search_limit
                and all_text[start] not in self.sentence_endings
            ):
                if all_text[start] in self.word_breaks:
                    last_word = start
                start -= 1
            if all_text[start] not in self.sentence_endings and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield from split_page_by_max_tokens(
                page_num=find_page(start), text=section_text, max_tokens=self.max_tokens_per_section
            )

            last_table_start = section_text.rfind("<table")
            if last_table_start > 2 * self.sentence_search_limit and last_table_start > section_text.rfind("</table"):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
                # If last table starts inside section_overlap, keep overlapping
                if self.verbose:
                    print(
                        f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}"
                    )
                start = min(end - self.section_overlap, start + last_table_start)
            else:
                start = end - self.section_overlap

        if start + self.section_overlap < end:
            yield from split_page_by_max_tokens(
                page_num=find_page(start), text=all_text[start:end], max_tokens=self.max_tokens_per_section
            )


class SimpleTextSplitter(TextSplitter):
    """
    Class that splits pages into smaller chunks based on a max object length. It is not aware of the content of the page.
    This is required because embedding models may not be able to analyze an entire page at once
    """

    def __init__(self, max_object_length: int = 1000, verbose: bool = False):
        self.max_object_length = max_object_length
        self.verbose = verbose

    def split_pages(self, pages: List[Page]) -> Generator[SplitPage, None, None]:
        all_text = "".join(page.text for page in pages)
        if len(all_text.strip()) == 0:
            return

        length = len(all_text)
        if length <= self.max_object_length:
            yield SplitPage(page_num=0, text=all_text)
            return

        # its too big, so we need to split it
        for i in range(0, length, self.max_object_length):
            yield SplitPage(page_num=i // self.max_object_length, text=all_text[i : i + self.max_object_length])
        return
