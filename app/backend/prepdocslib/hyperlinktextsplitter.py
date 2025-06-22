import logging
import re
from collections.abc import Generator
from typing import List, Tuple

import tiktoken

from .page import Page, SplitPage
from .textsplitter import SentenceTextSplitter

logger = logging.getLogger("scripts")


class HyperlinkAwareTextSplitter(SentenceTextSplitter):
    """
    Text splitter that preserves hyperlinks during chunking
    """

    def __init__(self, max_tokens_per_section: int = 500, add_target_blank: bool = True):
        super().__init__(max_tokens_per_section)
        # More comprehensive pattern that handles various link formats
        self.hyperlink_pattern = re.compile(
            r'<a\s+(?:[^>]*?\s+)?href\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )
        self.add_target_blank = add_target_blank

    def split_page_by_max_tokens(self, page_num: int, text: str) -> Generator[SplitPage, None, None]:
        """
        Split text while preserving hyperlinks
        """
        # Optionally transform hyperlinks to add target="_blank"
        if self.add_target_blank:
            text = self._add_target_blank_to_links(text)
        
        # Extract hyperlinks and their positions
        hyperlinks = list(self.hyperlink_pattern.finditer(text))
        
        # If no hyperlinks, use the parent method
        if not hyperlinks:
            yield from super().split_page_by_max_tokens(page_num, text)
            return

        tokens = tiktoken.encoding_for_model("text-embedding-ada-002").encode(text)
        if len(tokens) <= self.max_tokens_per_section:
            yield SplitPage(page_num=page_num, text=text)
            return

        # Split text while keeping hyperlinks intact
        yield from self._split_preserving_hyperlinks(page_num, text, hyperlinks)

    def _add_target_blank_to_links(self, text: str) -> str:
        """
        Add target="_blank" and rel="noopener noreferrer" to all hyperlinks
        """
        def replace_link(match):
            full_match = match.group(0)
            
            # Check if target="_blank" already exists
            if 'target="_blank"' in full_match or "target='_blank'" in full_match:
                return full_match
            
            # Extract the opening tag and closing tag
            href_match = re.search(r'href="([^"]*)"', full_match)
            if not href_match:
                return full_match
            
            # Insert target="_blank" and rel="noopener noreferrer" after href
            new_link = full_match.replace(
                href_match.group(0), 
                f'{href_match.group(0)} target="_blank" rel="noopener noreferrer"'
            )
            
            return new_link
        
        # Use the same pattern as the class-level pattern
        return self.hyperlink_pattern.sub(replace_link, text)

    def _split_preserving_hyperlinks(self, page_num: int, text: str, hyperlinks: List[re.Match]) -> Generator[SplitPage, None, None]:
        """
        Split text ensuring hyperlinks are not broken across chunks
        """
        text_length = len(text)
        start = 0
        
        while start < text_length:
            # Calculate the ideal end position
            ideal_end = min(start + self.max_section_length, text_length)
            
            # Find the best split position that doesn't break hyperlinks
            split_end = self._find_safe_split_position(text, start, ideal_end, hyperlinks)
            
            if split_end <= start:
                # Fallback: take at least one hyperlink or sentence
                split_end = self._find_minimum_split(text, start, hyperlinks)
            
            section_text = text[start:split_end].strip()
            
            if section_text:
                yield SplitPage(page_num=page_num, text=section_text)
            
            # Move to next section with overlap
            start = max(start + 1, split_end - self.section_overlap)

    def _find_safe_split_position(self, text: str, start: int, ideal_end: int, hyperlinks: List[re.Match]) -> int:
        """
        Find a position to split that doesn't break hyperlinks
        """
        # Check if the ideal end position is within a hyperlink
        for hyperlink in hyperlinks:
            link_start, link_end = hyperlink.span()
            
            # If the split would occur within a hyperlink, adjust
            if link_start < ideal_end < link_end:
                # Try to end before the hyperlink
                if link_start > start + self.max_section_length // 2:
                    return self._find_sentence_boundary_before(text, link_start, start)
                # Otherwise, include the entire hyperlink
                else:
                    return self._find_sentence_boundary_after(text, link_end, len(text))
        
        # No hyperlink conflict, find sentence boundary
        return self._find_sentence_boundary_before(text, ideal_end, start)

    def _find_sentence_boundary_before(self, text: str, position: int, min_position: int) -> int:
        """
        Find the nearest sentence ending before the given position
        """
        for i in range(position - 1, min_position - 1, -1):
            if text[i] in self.sentence_endings:
                return i + 1
        
        # Fallback to word boundary
        for i in range(position - 1, min_position - 1, -1):
            if text[i] in self.word_breaks:
                return i + 1
        
        return position

    def _find_sentence_boundary_after(self, text: str, position: int, max_position: int) -> int:
        """
        Find the nearest sentence ending after the given position
        """
        for i in range(position, min(max_position, position + self.sentence_search_limit)):
            if text[i] in self.sentence_endings:
                return i + 1
        
        return min(position + self.max_section_length, max_position)

    def _find_minimum_split(self, text: str, start: int, hyperlinks: List[re.Match]) -> int:
        """
        Find minimum viable split position (at least one complete element)
        """
        # Find the first complete hyperlink after start
        for hyperlink in hyperlinks:
            link_start, link_end = hyperlink.span()
            if link_start >= start:
                return link_end
        
        # Fallback to sentence or word boundary
        for i in range(start + 1, len(text)):
            if text[i] in self.sentence_endings:
                return i + 1
        
        return min(start + self.max_section_length, len(text))