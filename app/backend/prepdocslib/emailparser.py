"""
Email parser for MSG and EML files.
Compatible with the prepdocs pipeline structure.
"""
import logging
import email
from email import policy
from typing import AsyncGenerator, IO, Union, Optional
import extract_msg
from io import BytesIO
import re

from .page import Page

logger = logging.getLogger(__name__)


class EmailParser:
    """Parser for EML email files."""
    
    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parse EML file content."""
        try:
            # Read bytes from IO object
            content_bytes = content.read()
            # Parse email from bytes
            msg = email.message_from_bytes(content_bytes, policy=policy.default)
            
            # Extract email metadata and body
            text_parts = []
            
            # Add headers
            text_parts.append(f"From: {msg.get('From', 'Unknown')}")
            text_parts.append(f"To: {msg.get('To', 'Unknown')}")
            text_parts.append(f"Subject: {msg.get('Subject', 'No Subject')}")
            text_parts.append(f"Date: {msg.get('Date', 'Unknown')}")
            text_parts.append("\n" + "="*80 + "\n")
            
            # Extract body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # Get text content
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body = part.get_content()
                            text_parts.append(body)
                        except Exception as e:
                            logger.warning(f"Could not extract text part: {e}")
                    
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        # Optionally extract HTML (you may want to strip HTML tags)
                        try:
                            html_body = part.get_content()
                            # Simple HTML tag removal (consider using BeautifulSoup for better results)
                            import re
                            text_body = re.sub('<[^<]+?>', '', html_body)
                            text_parts.append(text_body)
                        except Exception as e:
                            logger.warning(f"Could not extract HTML part: {e}")
                    
                    # Note attachments
                    elif "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            text_parts.append(f"\n[Attachment: {filename}]")
            else:
                # Single part message
                try:
                    body = msg.get_content()
                    text_parts.append(body)
                except Exception as e:
                    logger.warning(f"Could not extract message body: {e}")
            
            # Combine all parts
            full_text = "\n".join(text_parts)
            
            # Return as single page
            yield Page(page_num=0, offset=0, text=full_text)
            
        except Exception as e:
            logger.error(f"Error parsing EML file: {e}")
            raise ValueError(f"Failed to parse EML file: {e}")


class MsgParser:
    """Parser for MSG (Outlook) email files."""
    
    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        """Parse MSG file content."""
        try:
            # Read bytes from IO object and create BytesIO
            content_bytes = content.read()
            msg_file = BytesIO(content_bytes)
            
            # Parse MSG file
            msg = extract_msg.Message(msg_file)
            
            # Extract email metadata and body
            text_parts = []
            
            # Add headers
            text_parts.append(f"From: {msg.sender or 'Unknown'}")
            text_parts.append(f"To: {msg.to or 'Unknown'}")
            text_parts.append(f"Subject: {msg.subject or 'No Subject'}")
            text_parts.append(f"Date: {msg.date or 'Unknown'}")
            text_parts.append("\n" + "="*80 + "\n")
            
            # Add body (prefer plain text over HTML)
            if msg.body:
                text_parts.append(msg.body)
            elif msg.htmlBody:
                # Simple HTML tag removal
                import re
                text_body = re.sub('<[^<]+?>', '', msg.htmlBody)
                text_parts.append(text_body)
            
            # Note attachments
            if msg.attachments:
                text_parts.append("\n\nAttachments:")
                for attachment in msg.attachments:
                    text_parts.append(f"  - {attachment.longFilename or attachment.shortFilename}")
            
            # Combine all parts
            full_text = "\n".join(text_parts)
            
            # Clean up
            msg.close()
            
            # Return as single page
            yield Page(page_num=0, offset=0, text=full_text)
            
        except Exception as e:
            logger.error(f"Error parsing MSG file: {e}")
            raise ValueError(f"Failed to parse MSG file: {e}")