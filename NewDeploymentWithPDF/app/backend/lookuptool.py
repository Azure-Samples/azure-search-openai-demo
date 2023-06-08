from os import path
import csv
from langchain.agents import Tool
from langchain.callbacks.manager import Callbacks
from typing import Optional

class CsvLookupTool(Tool):
    data: dict[str, str] = {}

    def __init__(self, filename: path, key_field: str, name: str = "lookup", 
                 description: str = "useful to look up details given an input key as opposite to searching data with an unstructured question",
                 callbacks: Callbacks = None):
        super().__init__(name, self.lookup, description, callbacks=callbacks)
        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.data[row[key_field]] =  "\n".join([f"{i}:{row[i]}" for i in row])

    def lookup(self, key: str) -> Optional[str]:
        return self.data.get(key, "")
