import logging
from abc import ABC
from typing import Generator, List

import tiktoken

from .page import Page, SplitPage

logger = logging.getLogger("ingester")


class TextSplitter(ABC):
    """
    Splits a list of pages into smaller chunks
    :param pages: The pages to split
    :return: A generator of SplitPage
    """

    def split_pages(self, pages: List[Page]) -> Generator[SplitPage, None, None]:
        if False:
            yield  # pragma: no cover - this is necessary for mypy to type check


ENCODING_MODEL = "text-embedding-ada-002"

STANDARD_WORD_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

# See W3C document https://www.w3.org/TR/jlreq/#cl-01
CJK_WORD_BREAKS = [
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
]

STANDARD_SENTENCE_ENDINGS = [".", "!", "?"]

# See CL05 and CL06, based on JIS X 4051:2004
# https://www.w3.org/TR/jlreq/#cl-04
CJK_SENTENCE_ENDINGS = ["。", "！", "？", "‼", "⁇", "⁈", "⁉"]

# NB: text-embedding-3-XX is the same BPE as text-embedding-ada-002
bpe = tiktoken.encoding_for_model(ENCODING_MODEL)

DEFAULT_OVERLAP_PERCENT = 10  # See semantic search article for 10% overlap performance
DEFAULT_SECTION_LENGTH = 1000  # Roughly 400-500 tokens for English


class SentenceTextSplitter(TextSplitter):
    """
    Class that splits pages into smaller chunks. This is required because embedding models may not be able to analyze an entire page at once
    """

    def __init__(self, has_image_embeddings: bool, max_tokens_per_section: int = 500):
        self.sentence_endings = STANDARD_SENTENCE_ENDINGS + CJK_SENTENCE_ENDINGS
        self.word_breaks = STANDARD_WORD_BREAKS + CJK_WORD_BREAKS
        self.max_section_length = DEFAULT_SECTION_LENGTH
        self.sentence_search_limit = 100
        self.max_tokens_per_section = max_tokens_per_section
        self.section_overlap = self.max_section_length // DEFAULT_OVERLAP_PERCENT
        self.has_image_embeddings = has_image_embeddings

    def split_page_by_max_tokens(self, page_num: int, text: str) -> Generator[SplitPage, None, None]:
        """
        Recursively splits page by maximum number of tokens to better handle languages with higher token/word ratios.
        """
        tokens = bpe.encode(text)
        if len(tokens) <= self.max_tokens_per_section:
            # Section is already within max tokens, return
            yield SplitPage(page_num=page_num, text=text)
        else:
            # Start from the center and try and find the closest sentence ending by spiralling outward.
            # IF we get to the outer thirds, then just split in half with a 5% overlap
            start = int(len(text) // 2)
            pos = 0
            boundary = int(len(text) // 3)
            split_position = -1
            while start - pos > boundary:
                if text[start - pos] in self.sentence_endings:
                    split_position = start - pos
                    break
                elif text[start + pos] in self.sentence_endings:
                    split_position = start + pos
                    break
                else:
                    pos += 1

            if split_position > 0:
                first_half = text[: split_position + 1]
                second_half = text[split_position + 1 :]
            else:
                # Split page in half and call function again
                # Overlap first and second halves by DEFAULT_OVERLAP_PERCENT%
                middle = int(len(text) // 2)
                overlap = int(len(text) * (DEFAULT_OVERLAP_PERCENT / 100))
                first_half = text[: middle + overlap]
                second_half = text[middle - overlap :]
            yield from self.split_page_by_max_tokens(page_num, first_half)
            yield from self.split_page_by_max_tokens(page_num, second_half)

    def split_pages(self, pages: List[Page]) -> Generator[SplitPage, None, None]:
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
            yield from self.split_page_by_max_tokens(page_num=find_page(0), text=all_text)
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
            yield from self.split_page_by_max_tokens(page_num=find_page(start), text=section_text)

            last_table_start = section_text.rfind("<table")
            if last_table_start > 2 * self.sentence_search_limit and last_table_start > section_text.rfind("</table"):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
                # If last table starts inside section_overlap, keep overlapping
                logger.info(
                    f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}"
                )
                start = min(end - self.section_overlap, start + last_table_start)
            else:
                start = end - self.section_overlap

        if start + self.section_overlap < end:
            yield from self.split_page_by_max_tokens(page_num=find_page(start), text=all_text[start:end])


class SimpleTextSplitter(TextSplitter):
    """
    Class that splits pages into smaller chunks based on a max object length. It is not aware of the content of the page.
    This is required because embedding models may not be able to analyze an entire page at once
    """

    def __init__(self, max_object_length: int = 1000):
        self.max_object_length = max_object_length

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
