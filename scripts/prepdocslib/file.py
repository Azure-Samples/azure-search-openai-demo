import base64
import os
import re
from typing import IO, Optional


class File:
    """
    Represents a file stored either locally or in a data lake storage account
    This file might contain access control information about which users or groups can access it
    """

    def __init__(self, content: IO, acls: Optional[dict[str, list]] = None):
        self.content = content
        self.acls = acls or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def filename(self):
        return os.path.basename(self.content.name)

    def filename_to_id(self):
        filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", self.filename())
        filename_hash = base64.b16encode(self.filename().encode("utf-8")).decode("ascii")
        return f"file-{filename_ascii}-{filename_hash}"

    def close(self):
        if self.content:
            self.content.close()
