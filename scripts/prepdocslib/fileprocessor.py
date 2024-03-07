from dataclasses import dataclass

from .parser import Parser
from .textsplitter import TextSplitter


@dataclass(frozen=True)
class FileProcessor:
    parser: Parser
    splitter: TextSplitter
