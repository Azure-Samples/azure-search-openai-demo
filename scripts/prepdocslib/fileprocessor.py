from dataclasses import make_dataclass

FileProcessor = make_dataclass("FileProcessor", ["parser", "splitter"], frozen=True)

