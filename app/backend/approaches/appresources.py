import os
import json
import logging
from typing import Optional

import openai
from azure.data.tables.aio import TableClient

from core.modelhelper import get_token_limit

use_RAG = False

class AppResources:
    def __init__(
        self,
        table_client: TableClient,
        sourcepage_field: str,
        content_field: str,
    ):
        self.table_client = table_client 
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
