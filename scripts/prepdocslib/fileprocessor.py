from dataclasses import dataclass

from .textsplitter import TextSplitter
from .parser import Parser

@dataclass(frozen=True)
class FileProcessor:
    parser: Parser
    splitter: TextSplitter

