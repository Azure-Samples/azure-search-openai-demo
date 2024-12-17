import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "app/backend"))

import asyncio
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from quart import Quart

# Local imports
from eval_config import EvalConfig
from config import (
    CONFIG_CHAT_APPROACH,
    CONFIG_SEARCH_CLIENT,
    CONFIG_BLOB_CONTAINER_CLIENT,
    CONFIG_USER_BLOB_CONTAINER_CLIENT
)
from approaches.approach import Approach
from app import bp, setup_clients

async def create_RAG_eval_app():
    app = Quart(__name__)
    app.register_blueprint(bp)
    async with app.app_context():
        await setup_clients()
        return app
    
async def cleanup_clients(app: Quart) -> None:
    """Cleanup all app resources and clients"""
    # Close search client
    if hasattr(app.config[CONFIG_SEARCH_CLIENT], 'close'):
        await app.config[CONFIG_SEARCH_CLIENT].close()
        
    # Close blob container client
    if hasattr(app.config[CONFIG_BLOB_CONTAINER_CLIENT], 'close'):
        await app.config[CONFIG_BLOB_CONTAINER_CLIENT].close()

    # Close user blob container client
    if CONFIG_USER_BLOB_CONTAINER_CLIENT in app.config:
        if hasattr(app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT], 'close'):
            await app.config[CONFIG_USER_BLOB_CONTAINER_CLIENT].close()

    # Close any remaining sessions
    if hasattr(app, '_client_session'):
        await app._client_session.close()

@dataclass
class SearchResult:
    """Structure for search results"""
    sourcepage: str
    content: str

    @classmethod
    def from_doc(cls, doc: Dict[str, Any]) -> 'SearchResult':
        return cls(
            sourcepage=doc.get('sourcepage', 'unknown'),
            content=doc.get('content', '')
        )

@dataclass
class TestConfig:
    """Configuration for RAG testing"""
    retrieval_mode: str
    semantic_ranker: bool
    semantic_captions: bool
    top_k: int
    temperature: float
    suggest_followup: bool
    query_language: str
    query_speller: str
    max_concurrent: int

    @classmethod
    def from_env(cls, eval_config: EvalConfig) -> 'TestConfig':
        """Create configuration from environment variables"""

        return cls(
            retrieval_mode=os.getenv("USE_VECTORS", "").lower() != "false" and "hybrid" or "text",
            semantic_ranker=os.getenv("AZURE_SEARCH_SEMANTIC_RANKER", "free").lower() != "disabled",
            semantic_captions=os.getenv("AZURE_SEARCH_SEMANTIC_CAPTIONS", "").lower() == "true",
            top_k=int(os.getenv("AZURE_SEARCH_TOP_K", "3")),
            temperature=float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0")),
            suggest_followup=os.getenv("SUGGEST_FOLLOWUP_QUESTIONS", "").lower() == "true",
            query_language=os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us"),
            query_speller=os.getenv("AZURE_SEARCH_QUERY_SPELLER", "lexicon"),
            max_concurrent=eval_config.max_concurrent
        )

class RAG:
    """RAG system testing framework"""
    def __init__(self, app: Quart, config_path: Optional[Path] = None):
        self.eval_config = EvalConfig.from_file(config_path)
        self.app = app
        self.approach = cast(Approach, app.config[CONFIG_CHAT_APPROACH])
        self.config = TestConfig.from_env(self.eval_config)
        self.max_concurrent = self.config.max_concurrent
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    async def get_contexts(self,
                           top: int = 5,
                           _seed: int = 42) -> List[SearchResult]:
        """Retrieve reproducable contexts from search index"""
        contexts = []
        total_docs = await self.app.config[CONFIG_SEARCH_CLIENT].get_document_count()

        random.seed(_seed)
        # Generate random offsets
        if total_docs <= top:
            offsets = list(range(total_docs))
        else:
            offsets = random.sample(range(total_docs), k=top)

        # Retrieve documents at random offsets
        async with self.semaphore:
            for offset in offsets:
                result = await self.app.config[CONFIG_SEARCH_CLIENT].search(
                    search_text="*",
                    top=1,
                    skip=offset,
                    order_by=["id"]  # Ensure consistent ordering
                )
                async for doc in result:
                    contexts.append(SearchResult.from_doc(doc))

            return contexts

    async def ask_questions(self, questions: List[str]) -> Dict[str, Any]:
        """Run RAG testing on provided questions"""
        results = []
        async with self.semaphore:
            for question in questions:
                try:
                    result = await self._process_question(question)
                    results.append(result)
                except Exception as e:
                    print(f"Error processing question '{question}': {str(e)}")
                    raise
        return {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "num_questions": len(questions),
            },
            "results": results
        }

    async def _process_question(self, question: str) -> Dict[str, Any]:
        """Process a single question"""
        messages = [{"role": "user", "content": question}]
        context = {
            "overrides": {
                "retrieval_mode": self.config.retrieval_mode,
                "semantic_ranker": self.config.semantic_ranker,
                "semantic_captions": self.config.semantic_captions,
                "top": self.config.top_k,
                "temperature": self.config.temperature,
                "suggest_followup_questions": self.config.suggest_followup,
                "query_language": self.config.query_language,
                "query_speller": self.config.query_speller
            }
        }
        
        return await self.approach.run(
            messages=messages,
            context=context
        )