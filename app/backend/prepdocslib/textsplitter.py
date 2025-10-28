import logging
import re
from abc import ABC
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Optional

import tiktoken

from .page import Chunk, Page

logger = logging.getLogger("scripts")


class TextSplitter(ABC):
    """
    Splits a list of pages into smaller chunks.
    :param pages: The pages to split
    :return: A generator of Chunk
    """

    def split_pages(self, pages: list[Page]) -> Generator[Chunk, None, None]:
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


def _safe_concat(a: str, b: str) -> str:
    """Concatenate two non-empty segments, inserting a space only when both sides
    end/start with alphanumerics and no natural boundary exists.

    Rules:
    - Both input strings are expected to be non-empty
    - Preserve existing whitespace if either side already provides a boundary.
    - Do not insert a space after a closing HTML tag marker '>'.
    - If both boundary characters are alphanumeric, insert a single space.
    - Otherwise concatenate directly.
    """
    assert a and b, "_safe_concat expects non-empty strings"
    a_last = a[-1]
    b_first = b[0]
    if a_last.isspace() or b_first.isspace():  # pre-existing boundary
        return a + b
    if a_last == ">":  # HTML tag end acts as a boundary
        return a + b
    if a_last.isalnum() and b_first.isalnum():  # need explicit separator
        return a + " " + b
    return a + b


def _normalize_chunk(text: str, max_chars: int) -> str:
    """Normalize a non-figure chunk that may slightly exceed max_chars.

    Allows overflow for any chunk containing a <figure ...> tag (figures are atomic),
    trims leading spaces if they alone cause minor overflow, and as a final step
    removes a trailing space/newline when within a small tolerance (<=3 chars over).
    """
    lower = text.lower()
    if "<figure" in lower:
        return text  # never trim figure chunks
    if len(text) <= max_chars:
        return text
    trimmed = text
    while trimmed.startswith(" ") and len(trimmed) > max_chars:
        trimmed = trimmed[1:]
    if len(trimmed) > max_chars and len(trimmed) <= max_chars + 3:
        if trimmed.endswith(" ") or trimmed.endswith("\n"):
            trimmed = trimmed.rstrip()
    return trimmed


@dataclass
class _ChunkBuilder:
    """Accumulates sentence-like spans for a single page until size limits are reached.

    Responsibilities:
    - Track appended text fragments and their approximate token length.
    - Decide if a new span can be added without exceeding character or token thresholds.
    - Flush accumulated content into an output list as a `Chunk`.
    - Allow a figure block to be force-appended (even if it overflows) so that headings + figure stay together.

    Notes:
    - Character limit is soft (exact enforcement + later normalization); token limit is hard.
    - Token counts are computed by the caller and passed to `add`; this class stays agnostic of the encoder.
    """

    page_num: int
    max_chars: int
    max_tokens: int
    parts: list[str] = field(default_factory=list)
    token_len: int = 0

    def can_fit(self, text: str, token_count: int) -> bool:
        if not self.parts:  # always allow first span
            return token_count <= self.max_tokens and len(text) <= self.max_chars
        # Character + token constraints
        return (len("".join(self.parts)) + len(text) <= self.max_chars) and (
            self.token_len + token_count <= self.max_tokens
        )

    def add(self, text: str, token_count: int) -> bool:
        if not self.can_fit(text, token_count):
            return False
        self.parts.append(text)
        self.token_len += token_count
        return True

    def force_append(self, text: str):
        self.parts.append(text)

    def flush_into(self, out: list[Chunk]):
        if self.parts:
            chunk = "".join(self.parts)
            if chunk.strip():
                out.append(Chunk(page_num=self.page_num, text=chunk))
        self.parts.clear()
        self.token_len = 0

    # Convenience helpers for readability at call sites
    def has_content(self) -> bool:
        return bool(self.parts)

    def append_figure_and_flush(self, figure_text: str, out: list[Chunk]):
        """Append a figure (allowed to overflow) to current accumulation and flush in one step."""
        self.force_append(figure_text)
        self.flush_into(out)


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
        # Always-on semantic overlap percent (duplicated suffix of previous chunk), applied:
        # - Between chunks on the same page.
        # - Across page boundary ONLY if semantic continuation heuristics pass.
        self.semantic_overlap_percent = 10

    def _find_split_pos(self, text: str) -> tuple[int, bool]:
        """Find a good split position near midpoint.

        Returns (index, use_overlap_fallback).

        Priority:
        1. Sentence-ending punctuation near midpoint (scan outward within central third).
        2. Word-break character near midpoint (space / punctuation) within same window.
        3. Fallback: caller should use midpoint + overlap strategy.
        """
        length = len(text)
        if length < 4:
            return -1, True
        mid = length // 2
        window_limit = length // 3  # defines central region scan boundary

        # 1. Sentence endings
        pos = 0
        while mid - pos > window_limit:
            left = mid - pos
            right = mid + pos
            if left >= 0 and text[left] in self.sentence_endings:
                return left, False
            if right < length and text[right] in self.sentence_endings:
                return right, False
            pos += 1

        # 2. Word breaks
        pos = 0
        while mid - pos > window_limit:
            left = mid - pos
            right = mid + pos
            if left >= 0 and text[left] in self.word_breaks:
                return left, False
            if right < length and text[right] in self.word_breaks:
                return right, False
            pos += 1

        # 3. Fallback
        return -1, True

    def split_page_by_max_tokens(self, page_num: int, text: str) -> Generator[Chunk, None, None]:
        """Recursively split plain text by token count.

        Boundary preference order when an oversized span is encountered:
        1. Sentence-ending punctuation near midpoint.
        2. Word-break character near midpoint (space/punctuation) to avoid mid-word cuts.
        3. Midpoint split with symmetric overlap (DEFAULT_OVERLAP_PERCENT).
        """
        tokens = bpe.encode(text)
        if len(tokens) <= self.max_tokens_per_section:
            yield Chunk(page_num=page_num, text=text)
            return

        split_pos, use_overlap = self._find_split_pos(text)
        if not use_overlap and split_pos > 0:
            first_half = text[: split_pos + 1]
            second_half = text[split_pos + 1 :]
        else:
            middle = len(text) // 2
            overlap = int(len(text) * (DEFAULT_OVERLAP_PERCENT / 100))
            first_half = text[: middle + overlap]
            second_half = text[middle - overlap :]

        yield from self.split_page_by_max_tokens(page_num, first_half)
        yield from self.split_page_by_max_tokens(page_num, second_half)

    def _is_heading_like(self, line: str) -> bool:
        """Heuristic heading detector used to suppress cross-page semantic overlap when a new section starts."""
        line_str = line.strip()
        if not line_str:
            return False
        if line_str.startswith("#"):
            return True
        # Short Title Case or ALL CAPS lines (limited word count) often represent headings
        if len(line_str) <= 80 and (line_str.isupper() or (line_str.istitle() and len(line_str.split()) <= 12)):
            return True
        import re as _re

        # Numbered / roman numeral list or section forms: '1. ', 'II) ', 'III. '
        if _re.match(r"^(?:\d+|[IVXLCM]+)[.)]\s", line_str):
            return True
        if line_str.startswith(("- ", "* ", "• ")):
            return True
        return False

    def _should_cross_page_overlap(self, prev: Chunk, nxt: Chunk) -> bool:
        if not prev or not nxt:
            return False
        if "<figure" in prev.text.lower() or "<figure" in nxt.text[:40].lower():
            return False
        prev_last = prev.text.rstrip()[-1:] if prev.text.rstrip() else ""
        if prev_last in self.sentence_endings:  # previous chunk ended cleanly
            return False
        nxt_stripped = nxt.text.lstrip()
        if not nxt_stripped:
            return False
        first_char = nxt_stripped[0]
        if not first_char.islower():  # treat uppercase start as likely new section
            return False
        first_line = nxt_stripped.splitlines()[0]
        if self._is_heading_like(first_line):
            return False
        return True

    def _append_overlap(self, prev_chunk: Chunk, next_chunk: Chunk) -> Chunk:
        """Return a modified copy of prev_chunk whose text has an appended semantic
        overlap prefix from next_chunk; next_chunk itself is left unchanged so it
        continues to start at its natural sentence boundary.

        Strategy:
        - Take ~semantic_overlap_percent tail size (in chars) from the START of next_chunk.
        - Extend that region forward to the first sentence-ending (preferred) or word break
          so we end on a natural boundary (avoid chopping mid-word/mid-sentence).
        - Refuse overlap if either chunk contains a <figure> to avoid duplicating figures.
        - Enforce hard token + soft char limits; shrink overlap if necessary.
        """
        if not prev_chunk or not next_chunk:
            return prev_chunk
        if "<figure" in prev_chunk.text.lower() or "<figure" in next_chunk.text[:60].lower():
            return prev_chunk

        target = int(self.max_section_length * self.semantic_overlap_percent / 100)
        if target <= 0:
            return prev_chunk

        base_prefix = next_chunk.text[:target]
        if not base_prefix.strip():  # nothing meaningful to append
            return prev_chunk

        # Grow prefix up to 2x target to reach a sentence end / word break boundary
        extension_limit = min(len(next_chunk.text), target * 2)
        prefix = base_prefix
        boundary_found = False
        for i in range(target, extension_limit):
            ch = next_chunk.text[i]
            prefix += ch
            if ch in self.sentence_endings:
                boundary_found = True
                break
            if ch in self.word_breaks and i - target > 20:  # fallback boundary after some progress
                boundary_found = True
                break
        if not boundary_found:
            # Trim trailing partial word if we stopped without boundary
            while prefix and prefix[-1].isalnum() and len(prefix) > target:
                prefix = prefix[:-1]

        # Avoid appending text that already exists at end (rare but possible due to prior operations)
        if prev_chunk.text.endswith(prefix):
            return prev_chunk

        candidate = prev_chunk.text + prefix
        max_chars = int(self.max_section_length * 1.2)
        if len(candidate) > max_chars or len(bpe.encode(candidate)) > self.max_tokens_per_section:
            # Attempt to shrink prefix at word / sentence boundaries from its start
            shrink = prefix
            while shrink and (
                len(prev_chunk.text + shrink) > max_chars
                or len(bpe.encode(prev_chunk.text + shrink)) > self.max_tokens_per_section
            ):
                cut_index = 1
                for i, ch in enumerate(shrink):
                    if ch in self.word_breaks or ch in self.sentence_endings:
                        cut_index = i + 1
                        break
                shrink = shrink[:-cut_index] if cut_index < len(shrink) else ""
            if not shrink:
                return prev_chunk
            candidate = prev_chunk.text + shrink
            if len(candidate) > max_chars or len(bpe.encode(candidate)) > self.max_tokens_per_section:
                return prev_chunk
        return Chunk(page_num=prev_chunk.page_num, text=candidate)

    def split_pages(self, pages: list[Page]) -> Generator[Chunk, None, None]:
        """Split each page into semantic chunks using token-aware accumulation with atomic figures.

        Strategy (per page):
        1. Extract balanced <figure>...</figure> blocks as atomic "figure" blocks.
        2. Treat intervening text as "text" blocks.
        3. For text blocks, break into sentence-ish spans (using sentence ending chars) and accumulate
        until adding the next span would exceed either character or token limit. Flush when needed.
        4. When a figure block arrives:
           - If there is accumulated text (builder), append the figure even if this exceeds token limit and flush.
           - If no accumulated text, emit the figure as its own chunk.
        5. Ignore token limits for any chunk that contains a figure (never split figures).
        This avoids partial/duplicated figures and keeps headings with their following figure when space permits.
        """
        figure_regex = re.compile(r"<figure.*?</figure>", re.IGNORECASE | re.DOTALL)
        previous_chunk: Optional[Chunk] = None

        for page in pages:
            raw = page.text or ""
            if not raw.strip():
                continue

            # Build ordered list of blocks: (type, text)
            blocks: list[tuple[str, str]] = []
            last = 0
            for m in figure_regex.finditer(raw):
                if m.start() > last:
                    blocks.append(("text", raw[last : m.start()]))
                blocks.append(("figure", m.group()))
                last = m.end()
            if last < len(raw):
                blocks.append(("text", raw[last:]))

            page_chunks: list[Chunk] = []
            builder = _ChunkBuilder(
                page_num=page.page_num,
                max_chars=self.max_section_length,
                max_tokens=self.max_tokens_per_section,
            )

            for btype, btext in blocks:
                if btype == "figure":
                    if builder.has_content():
                        # Append figure to existing text (allow overflow) and flush
                        builder.append_figure_and_flush(btext, page_chunks)
                    else:
                        # Emit figure standalone
                        if btext.strip():
                            page_chunks.append(Chunk(page_num=page.page_num, text=btext))
                    continue

                # Process text block: split into sentence-like spans
                spans: list[str] = []
                current_chars: list[str] = []
                for ch in btext:
                    current_chars.append(ch)
                    if ch in self.sentence_endings:
                        spans.append("".join(current_chars))
                        current_chars = []
                if current_chars:  # remaining tail
                    spans.append("".join(current_chars))

                for span in spans:
                    span_tokens = len(bpe.encode(span))
                    # If a single span itself exceeds token limit (rare, very long sentence), split it directly
                    if span_tokens > self.max_tokens_per_section:
                        builder.flush_into(page_chunks)
                        for chunk in self.split_page_by_max_tokens(page.page_num, span):
                            page_chunks.append(chunk)
                        continue
                    if not builder.add(span, span_tokens):
                        # Flush and retry (guaranteed to fit because span_tokens <= limit)
                        builder.flush_into(page_chunks)
                        if not builder.add(span, span_tokens):
                            page_chunks.append(Chunk(page_num=page.page_num, text=span))

            # Flush any trailing builder content
            builder.flush_into(page_chunks)

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
                        previous_chunk = Chunk(page_num=previous_chunk.page_num, text=combined_text)
                        page_chunks = page_chunks[1:]
                    else:
                        # Cannot merge whole due to token/char limits; attempt to shift trailing partial sentence
                        # from previous chunk into the first new chunk so that sentence does not start mid-way.
                        prev_text = previous_chunk.text
                        # Find last full sentence ending in previous chunk.
                        last_end = max((prev_text.rfind(se) for se in self.sentence_endings), default=-1)
                        fragment_start = last_end + 1 if last_end != -1 and last_end < len(prev_text) - 1 else 0
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
                                page_chunks[0] = Chunk(
                                    page_num=page_chunks[0].page_num,
                                    text=_safe_concat(move_fragment, first_new_text),
                                )
                            # Adjust previous_chunk retained portion
                            if retained.strip():
                                previous_chunk = Chunk(page_num=previous_chunk.page_num, text=retained)
                            else:
                                previous_chunk = None
                            # Insert leftover fragment as its own chunk (split if needed) BEFORE modified first_new
                            if leftover_fragment.strip():
                                # Ensure leftover respects limits by splitting if needed
                                leftover_pages = list(
                                    self.split_page_by_max_tokens(page_chunks[0].page_num, leftover_fragment)
                                )
                                # Insert these before current first chunk
                                page_chunks = leftover_pages + page_chunks

            # Normalize chunks (non-figure) that barely exceed char limit due to added boundary space
            max_chars = int(self.max_section_length * 1.2)
            if previous_chunk:
                previous_chunk = Chunk(
                    page_num=previous_chunk.page_num, text=_normalize_chunk(previous_chunk.text, max_chars)
                )
            if page_chunks:
                page_chunks = [
                    Chunk(page_num=chunk.page_num, text=_normalize_chunk(chunk.text, max_chars))
                    for chunk in page_chunks
                ]

            # Apply semantic overlap duplication (append style). We append a small
            # prefix of the NEXT chunk onto the PREVIOUS chunk, keeping natural starts.
            if self.semantic_overlap_percent > 0:
                # Cross-page overlap: modify previous_chunk (look-ahead to first new chunk)
                if previous_chunk and page_chunks and self._should_cross_page_overlap(previous_chunk, page_chunks[0]):
                    previous_chunk = self._append_overlap(previous_chunk, page_chunks[0])

                # Intra-page overlaps
                if len(page_chunks) > 1:
                    for i in range(1, len(page_chunks)):
                        prev_c = page_chunks[i - 1]
                        curr_c = page_chunks[i]
                        if "<figure" in prev_c.text.lower() or "<figure" in curr_c.text.lower():
                            continue
                        page_chunks[i - 1] = self._append_overlap(prev_c, curr_c)

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

    def split_pages(self, pages: list[Page]) -> Generator[Chunk, None, None]:
        all_text = "".join(page.text for page in pages)
        if len(all_text.strip()) == 0:
            return

        length = len(all_text)
        if length <= self.max_object_length:
            yield Chunk(page_num=0, text=all_text)
            return

        # its too big, so we need to split it
        for i in range(0, length, self.max_object_length):
            yield Chunk(page_num=i // self.max_object_length, text=all_text[i : i + self.max_object_length])
        return
