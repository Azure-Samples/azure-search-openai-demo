"""
Citation Filter Service

Filters citations to only include those actually used in the answer text.
"""

import re
from typing import List, Set


def extract_citations_from_text(text: str) -> Set[str]:
    """
    Extract citations from answer text.
    
    Citations can be in formats:
    - [document.pdf#page=1]
    - [https://example.com]
    - [document.pdf#page=1(image.png)]
    
    Args:
        text: The answer text from the LLM
        
    Returns:
        Set of citation strings found in the text
    """
    citations = set()
    
    # Pattern to match citations in square brackets
    # Matches: [anything inside brackets]
    citation_pattern = r'\[([^\]]+)\]'
    
    matches = re.findall(citation_pattern, text)
    for match in matches:
        # Remove any image filename in parentheses if present
        # e.g., "doc.pdf#page=1(image.png)" -> "doc.pdf#page=1"
        if '(' in match and ')' in match:
            # Extract the part before the opening parenthesis
            citation = match.split('(')[0].strip()
        else:
            citation = match.strip()
        
        if citation:  # Only add non-empty citations
            citations.add(citation)
    
    return citations


def filter_citations_by_answer(
    all_citations: List[str],
    answer_text: str
) -> List[str]:
    """
    Filter citations to only include those actually used in the answer text.
    
    Args:
        all_citations: List of all citations from retrieved documents
        answer_text: The answer text from the LLM
        
    Returns:
        Filtered list of citations that appear in the answer text
    """
    if not answer_text or not all_citations:
        return all_citations or []
    
    # Extract citations from answer text
    citations_in_answer = extract_citations_from_text(answer_text)
    
    if not citations_in_answer:
        # If no citations found in answer, return all citations (fallback)
        return all_citations
    
    # Filter citations to only those found in the answer
    filtered = []
    for citation in all_citations:
        # Check if this citation appears in the answer
        # Handle both exact match and partial match (e.g., citation might be "doc.pdf#page=1" 
        # and answer might have "[doc.pdf#page=1]")
        citation_normalized = citation.strip()
        
        # Check exact match
        if citation_normalized in citations_in_answer:
            filtered.append(citation)
        else:
            # Check if citation is a substring of any citation in answer
            # or if any citation in answer is a substring of this citation
            for answer_citation in citations_in_answer:
                if (citation_normalized in answer_citation or 
                    answer_citation in citation_normalized):
                    filtered.append(citation)
                    break
    
    # If no matches found, return all citations (fallback to avoid losing all citations)
    return filtered if filtered else all_citations

