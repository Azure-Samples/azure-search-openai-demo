import logging
import re
from collections.abc import AsyncGenerator
from typing import Dict, List, Optional, Union
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from io import BytesIO, BufferedReader

from .page import Page
from .parser import Parser

logger = logging.getLogger("scripts")


class DocxHyperlinkParser(Parser):
    """
    Parser that extracts text from DOCX files while preserving hyperlinks
    """

    def __init__(self):
        self.hyperlink_pattern = re.compile(r'<a href="([^"]*)"[^>]*>([^<]*)</a>')

    async def parse(self, content: Union[bytes, BufferedReader]) -> AsyncGenerator[Page, None]:
        try:
            # Convert BufferedReader to bytes if necessary
            if isinstance(content, BufferedReader):
                content_bytes = content.read()
            else:
                content_bytes = content
                
            # Parse DOCX file
            docx_content = self._extract_text_with_hyperlinks(content_bytes)
            
            if docx_content.strip():
                yield Page(page_num=0, offset=0, text=docx_content)
        except Exception as e:
            logger.warning(f"Error parsing DOCX content: {e}")
            return

    def _extract_text_with_hyperlinks(self, content: bytes) -> str:
        """Extract text from DOCX while preserving hyperlinks as HTML markup"""
        try:
            with ZipFile(BytesIO(content)) as docx_zip:
                # Read the main document
                document_xml = docx_zip.read('word/document.xml')
                
                # Read relationships to get hyperlink targets
                relationships = self._parse_relationships(docx_zip)
                
                # Parse the document XML
                root = ET.fromstring(document_xml)
                
                # Define namespaces
                namespaces = {
                    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
                }
                
                text_parts = []
                
                # Extract text and hyperlinks
                for paragraph in root.findall('.//w:p', namespaces):
                    paragraph_text = self._extract_paragraph_with_links(
                        paragraph, relationships, namespaces
                    )
                    if paragraph_text.strip():
                        text_parts.append(paragraph_text)
                
                return '\n\n'.join(text_parts)
                
        except Exception as e:
            logger.error(f"Error extracting DOCX content: {e}")
            return ""

    def _parse_relationships(self, docx_zip: ZipFile) -> Dict[str, str]:
        """Parse relationships file to get hyperlink targets"""
        relationships = {}
        try:
            rels_xml = docx_zip.read('word/_rels/document.xml.rels')
            root = ET.fromstring(rels_xml)
            
            for relationship in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                rel_id = relationship.get('Id')
                target = relationship.get('Target')
                rel_type = relationship.get('Type')
                
                # Only store hyperlink relationships
                if rel_type == 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink':
                    relationships[rel_id] = target
                    
        except Exception as e:
            logger.warning(f"Could not parse relationships: {e}")
            
        return relationships

    def _extract_paragraph_with_links(self, paragraph, relationships: Dict[str, str], namespaces: Dict[str, str]) -> str:
        """Extract text from a paragraph, preserving hyperlinks"""
        text_parts = []
        
        # Process all elements in the paragraph
        for elem in paragraph.iter():
            if elem.tag.endswith('hyperlink'):
                # This is a hyperlink element
                rel_id = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                link_text = ''.join(t.text for t in elem.findall('.//w:t', namespaces) if t.text)
                
                if rel_id and rel_id in relationships:
                    url = relationships[rel_id]
                    text_parts.append(f'<a href="{url}">{link_text}</a>')
                else:
                    # Fallback to plain text if relationship not found
                    text_parts.append(link_text)
            elif elem.tag.endswith('t') and elem.text:
                # Regular text element - only add if it's not within a hyperlink
                parent = elem.find('..')
                grandparent = parent.find('..') if parent is not None else None
                if grandparent is None or not grandparent.tag.endswith('hyperlink'):
                    text_parts.append(elem.text)
        
        return ''.join(text_parts)