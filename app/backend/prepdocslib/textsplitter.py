import logging
import re
from abc import ABC
from collections.abc import Generator

import tiktoken

from .page import Page, SplitPage

logger = logging.getLogger("scripts")


class TextSplitter(ABC):
    """
    Splits a list of pages into smaller chunks
    :param pages: The pages to split
    :return: A generator of SplitPage
    """

    def split_pages(self, pages: list[Page]) -> Generator[SplitPage, None, None]:
        if False:  # pragma: no cover - this is necessary for mypy to type check
            yield


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

    def __init__(self, max_tokens_per_section: int = 500):
        self.sentence_endings = STANDARD_SENTENCE_ENDINGS + CJK_SENTENCE_ENDINGS
        self.word_breaks = STANDARD_WORD_BREAKS + CJK_WORD_BREAKS
        self.max_section_length = DEFAULT_SECTION_LENGTH
        self.sentence_search_limit = 100
        self.max_tokens_per_section = max_tokens_per_section
        self.section_overlap = int(self.max_section_length * DEFAULT_OVERLAP_PERCENT / 100)

    def split_page_by_max_tokens(
        self, page_num: int, text: str, *, allow_figure_processing: bool = True
    ) -> Generator[SplitPage, None, None]:
        """Recursively split text by token count, keeping complete <figure> blocks intact.

        Rules:
        - Balanced <figure>...</figure> blocks are emitted whole even if they exceed max_tokens_per_section.
        - Text outside figures is split normally.
        - Unbalanced figure markup (e.g. a truncated figure) is treated as normal text to avoid infinite recursion.
        """
        lower_text = text.lower()
        if allow_figure_processing and "<figure" in lower_text:
            figure_pattern = re.compile(r"<figure.*?</figure>", re.IGNORECASE | re.DOTALL)
            parts: list[str] = []
            idx = 0
            for match in figure_pattern.finditer(text):
                if match.start() > idx:
                    parts.append(text[idx : match.start()])
                parts.append(match.group())
                idx = match.end()
            if idx < len(text):
                parts.append(text[idx:])
            # Merge any balanced figure block into the preceding chunk so headings/intro stay with figure.
            merged_chunks: list[str] = []
            current: str = ""
            for segment in parts:
                seg_lower = segment.lower()
                is_balanced_figure = "<figure" in seg_lower and seg_lower.count("<figure") == seg_lower.count(
                    "</figure>"
                )
                # Consolidated handling: always accumulate into current first, then emit/reset if it's a figure block.
                if current:
                    current += segment
                else:
                    current = segment
                if is_balanced_figure:
                    merged_chunks.append(current)
                    current = ""
            if current.strip():
                merged_chunks.append(current)

            for chunk in merged_chunks:
                chunk_lower = chunk.lower()
                if "<figure" in chunk_lower and chunk_lower.count("<figure") == chunk_lower.count("</figure>"):
                    # Entire chunk contains (at least one) complete figure; emit ignoring token limit.
                    yield SplitPage(page_num=page_num, text=chunk)
                else:
                    # Recurse to split if still oversized and has no complete figure.
                    yield from self.split_page_by_max_tokens(page_num, chunk, allow_figure_processing=False)
            return

        tokens = bpe.encode(text)
        if len(tokens) <= self.max_tokens_per_section:
            yield SplitPage(page_num=page_num, text=text)
            return

        # Find a sentence boundary near the middle
        start = int(len(text) // 2)
        pos = 0
        boundary = int(len(text) // 3)
        split_position = -1
        while start - pos > boundary:
            left = start - pos
            right = start + pos
            if left >= 0 and text[left] in self.sentence_endings:
                split_position = left
                break
            if right < len(text) and text[right] in self.sentence_endings:
                split_position = right
                break
            pos += 1

        if split_position > 0:
            first_half = text[: split_position + 1]
            second_half = text[split_position + 1 :]
        else:
            middle = int(len(text) // 2)
            overlap = int(len(text) * (DEFAULT_OVERLAP_PERCENT / 100))
            first_half = text[: middle + overlap]
            second_half = text[middle - overlap :]
        yield from self.split_page_by_max_tokens(page_num, first_half, allow_figure_processing=False)
        yield from self.split_page_by_max_tokens(page_num, second_half, allow_figure_processing=False)

    def split_pages(self, pages: list[Page]) -> Generator[SplitPage, None, None]:
        """Split each page into semantic chunks using token-aware accumulation with atomic figures.

        Strategy (per page):
        1. Extract balanced <figure>...</figure> blocks as atomic "figure" blocks.
        2. Treat intervening text as "text" blocks.
        3. For text blocks, break into sentence-ish units (using sentence ending chars) and accumulate
           until adding the next unit would exceed either character or token limit. Flush when needed.
        4. When a figure block arrives:
           - If there is accumulated text (builder), append the figure even if this exceeds token limit and flush.
           - If no accumulated text, emit the figure as its own chunk.
        5. Ignore token limits for any chunk that contains a figure (never split figures).
        This avoids partial/duplicated figures and keeps headings with their following figure when space permits.
        """
        figure_regex = re.compile(r"<figure.*?</figure>", re.IGNORECASE | re.DOTALL)

        previous_chunk: SplitPage | None = None

        for page in pages:
            raw = page.text or ""
            if not raw.strip():
                continue

            def _safe_concat(a: str, b: str) -> str:
                """Concatenate two non-empty segments, inserting a space only when both sides
                end/start with alphanumerics and no natural boundary exists. (Empty inputs are
                never passed here by construction.)"""
                a_last = a[-1]
                b_first = b[0]
                # If either already has whitespace boundary, just concat
                if a_last.isspace() or b_first.isspace():
                    return a + b
                # If a ends with '>' (HTML tag) we assume boundary is intentional.
                if a_last == ">":
                    return a + b
                # If both alnum, insert space.
                if a_last.isalnum() and b_first.isalnum():
                    return a + " " + b
                return a + b

            # 1. Build ordered list of blocks: (type, text)
            blocks: list[tuple[str, str]] = []
            last = 0
            for m in figure_regex.finditer(raw):
                if m.start() > last:
                    blocks.append(("text", raw[last : m.start()]))
                blocks.append(("figure", m.group()))
                last = m.end()
            if last < len(raw):
                blocks.append(("text", raw[last:]))

            # Accumulated chunks for this page
            page_chunks: list[SplitPage] = []

            # Builder state for text accumulation
            builder: list[str] = []
            builder_token_len = 0

            def flush_builder_to_page():
                nonlocal builder, builder_token_len
                if builder:
                    text_chunk = "".join(builder)
                    if text_chunk.strip():
                        page_chunks.append(SplitPage(page_num=page.page_num, text=text_chunk))
                builder = []
                builder_token_len = 0

            for btype, btext in blocks:
                if btype == "figure":
                    if builder:
                        # Append figure to existing text (allow overflow) and flush
                        builder.append(btext)
                        flush_builder_to_page()
                    else:
                        # Emit figure standalone
                        if btext.strip():
                            page_chunks.append(SplitPage(page_num=page.page_num, text=btext))
                    continue

                # Process text block: split into sentence-like units
                units: list[str] = []
                current_chars: list[str] = []
                for ch in btext:
                    current_chars.append(ch)
                    if ch in self.sentence_endings:
                        units.append("".join(current_chars))
                        current_chars = []
                if current_chars:  # remaining tail
                    units.append("".join(current_chars))

                for unit in units:
                    unit_tokens = len(bpe.encode(unit))
                    # If a single unit itself exceeds token limit (rare, very long sentence), split it directly
                    if unit_tokens > self.max_tokens_per_section:
                        flush_builder_to_page()
                        for sp in self.split_page_by_max_tokens(page.page_num, unit, allow_figure_processing=False):
                            page_chunks.append(sp)
                        continue
                    if builder and (
                        len("".join(builder)) + len(unit) > self.max_section_length
                        or builder_token_len + unit_tokens > self.max_tokens_per_section
                    ):
                        # Flush current builder before starting new one with this unit
                        flush_builder_to_page()
                    builder.append(unit)
                    builder_token_len += unit_tokens

            # Flush any trailing builder content
            flush_builder_to_page()

            # Attempt cross-page merge with previous_chunk (look-behind) if semantic continuation
            if previous_chunk and page_chunks:
                prev_last_char = previous_chunk.text.rstrip()[-1:] if previous_chunk.text.rstrip() else ""
                first_new = page_chunks[0]
                first_new_stripped = first_new.text.lstrip()
                first_char = first_new_stripped[:1]
                if (
                    prev_last_char
                    and prev_last_char not in self.sentence_endings
                    and not first_new_stripped.startswith("#")
                    and first_char
                    and first_char.islower()
                    and "<figure" not in first_new_stripped[:20].lower()
                ):
                    combined_text = _safe_concat(previous_chunk.text, first_new.text)
                    # Only merge if token limit respected (figures already handled earlier)
                    if len(bpe.encode(combined_text)) <= self.max_tokens_per_section and len(combined_text) <= int(
                        self.max_section_length * 1.2
                    ):
                        previous_chunk = SplitPage(page_num=previous_chunk.page_num, text=combined_text)
                        page_chunks = page_chunks[1:]
                    else:
                        # Cannot merge whole due to token/char limits; attempt to shift trailing partial sentence
                        # from previous chunk into the first new chunk so that sentence does not start mid-way.
                        prev_text = previous_chunk.text
                        # Find last full sentence ending in previous chunk.
                        last_end = max((prev_text.rfind(se) for se in self.sentence_endings), default=-1)
                        if last_end != -1 and last_end < len(prev_text) - 1:
                            # Trailing fragment starts after the sentence-ending punctuation.
                            fragment_start = last_end + 1
                        else:
                            # No sentence ending found (very long sentence) -> move entire previous chunk.
                            fragment_start = 0
                        # Only shift if this creates a better (non mid-sentence) boundary: ensure fragment is not empty
                        if fragment_start < len(prev_text):
                            fragment_full = prev_text[fragment_start:]
                            retained = prev_text[:fragment_start]
                            # Budget calculations for prepending
                            max_chars = int(self.max_section_length * 1.2)
                            first_new_text = page_chunks[0].text

                            # Determine allowable fragment length (char + token)
                            def fits(candidate: str) -> bool:
                                combined = candidate + first_new_text
                                if len(combined) > max_chars:
                                    return False
                                if len(bpe.encode(combined)) > self.max_tokens_per_section:
                                    return False
                                return True

                            move_fragment = fragment_full
                            if not fits(move_fragment):
                                # Hard trim path: fragment begins after the last sentence-ending punctuation
                                # of the previous chunk. Reduce to remaining character budget, then iteratively
                                # shrink until token constraints are satisfied.
                                remaining_chars = max_chars - len(first_new_text)  # always > 0 given builder invariants
                                move_fragment = move_fragment[:remaining_chars]
                                while (
                                    move_fragment
                                    and len(bpe.encode(move_fragment + first_new_text)) > self.max_tokens_per_section
                                ):
                                    move_fragment = (
                                        move_fragment[:-50] if len(move_fragment) > 50 else move_fragment[:-1]
                                    )
                            leftover_fragment = fragment_full[len(move_fragment) :]
                            # Prepend the allowed fragment
                            if move_fragment:
                                page_chunks[0] = SplitPage(
                                    page_num=page_chunks[0].page_num,
                                    text=_safe_concat(move_fragment, first_new_text),
                                )
                            # Adjust previous_chunk retained portion
                            if retained.strip():
                                previous_chunk = SplitPage(page_num=previous_chunk.page_num, text=retained)
                            else:
                                previous_chunk = None
                            # Insert leftover fragment as its own chunk (split if needed) BEFORE modified first_new
                            if leftover_fragment.strip():
                                # Ensure leftover respects limits by splitting if needed
                                leftover_pages = list(
                                    self.split_page_by_max_tokens(
                                        page_chunks[0].page_num, leftover_fragment, allow_figure_processing=False
                                    )
                                )
                                # Insert these before current first chunk
                                page_chunks = leftover_pages + page_chunks

            # Normalize chunks (non-figure) that barely exceed char limit due to added boundary space
            max_chars = int(self.max_section_length * 1.2)

            def _normalize(text: str) -> str:
                lower = text.lower()
                if "<figure" in lower:
                    return text  # allow overflow for figures
                if len(text) <= max_chars:
                    return text
                # Trim leading spaces first (most common cause after safe concat)
                trimmed = text
                while trimmed.startswith(" ") and len(trimmed) > max_chars:
                    trimmed = trimmed[1:]
                # As a fallback, if still barely over (<= max_chars+3), try removing a trailing space/newline
                if len(trimmed) > max_chars and len(trimmed) <= max_chars + 3:
                    if trimmed.endswith(" ") or trimmed.endswith("\n"):
                        trimmed = trimmed.rstrip()
                return trimmed

            if previous_chunk:
                previous_chunk = SplitPage(page_num=previous_chunk.page_num, text=_normalize(previous_chunk.text))
            if page_chunks:
                page_chunks = [SplitPage(page_num=sp.page_num, text=_normalize(sp.text)) for sp in page_chunks]

            # Emit previous_chunk now that merge opportunity considered
            if previous_chunk:
                yield previous_chunk

            # Keep last chunk as new previous (for next page merge);
            # emit all but last immediately.
            if page_chunks:
                if len(page_chunks) == 1:
                    previous_chunk = page_chunks[0]
                else:
                    yield from page_chunks[:-1]
                    previous_chunk = page_chunks[-1]
            else:
                previous_chunk = None

        # Emit any final held chunk
        if previous_chunk:
            yield previous_chunk


class SimpleTextSplitter(TextSplitter):
    """
    Class that splits pages into smaller chunks based on a max object length. It is not aware of the content of the page.
    This is required because embedding models may not be able to analyze an entire page at once
    """

    def __init__(self, max_object_length: int = 1000):
        self.max_object_length = max_object_length

    def split_pages(self, pages: list[Page]) -> Generator[SplitPage, None, None]:
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
