"""
Module for wrapping OpenAI models for use in DeepEval
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "app/backend"))

import asyncio
import instructor
from typing import Optional, Type, List, Tuple
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.models import DeepEvalBaseEmbeddingModel
from openai import AsyncAzureOpenAI as AsyncAzureOpenAIClient

from core.authentication import AuthenticationHelper


class AzureOpenAI(DeepEvalBaseLLM):
    """Wrapper for Azure OpenAI that supports both direct and app config initialization"""
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        client_auth: Optional[Tuple[AsyncAzureOpenAIClient, AuthenticationHelper]] = None,
        deployment_name: Optional[str] = None,
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
        max_concurrent: int = 2,
    ):
        self.model_name = deployment_name or model_name
        self.temperature = temperature
        self.semaphore = asyncio.Semaphore(max_concurrent)
        if client_auth:
            self.client = client_auth[0]
            self.auth_helper = client_auth[1]
        else:
            if not all([deployment_name, api_key, azure_endpoint]):
                raise ValueError("Must provide either client_auth or all direct initialization parameters")
            self.client = AsyncAzureOpenAIClient(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=api_version,
            )
            
        self.instructor_client = instructor.patch(self.client)

    def load_model(self):
        return self.instructor_client

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt: str,
                 schema: Optional[Type[BaseModel]]=None) -> BaseModel:
        response = self.instructor_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    response_model=schema
        )
        return response
    
    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def a_generate(self, prompt: str,
                         schema: Optional[Type[BaseModel]]=None) -> BaseModel:
        async with self.semaphore:
            response = await self.instructor_client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        response_model=schema
            )
            return response

    def get_model_name(self):
        return f"Azure OpenAI Model - {self.model_name}"

class AzureOpenAIEmbeddingModel(DeepEvalBaseEmbeddingModel):
    """Wrapper for Azure OpenAI embeddings that supports both direct and app config initialization"""
    def __init__(
        self,
        model_name: Optional[str] = None,
        client_auth: Optional[Tuple[AsyncAzureOpenAIClient, AuthenticationHelper]] = None,
        deployment_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        max_concurrent: int = 2,
    ):
        self.model_name = deployment_name or model_name
        self.semaphore = asyncio.Semaphore(max_concurrent)

        if client_auth:
            self.client = client_auth[0]
            self.auth_helper = client_auth[1]
        else:
            if not all([api_key, api_version, azure_endpoint]):
                raise ValueError("Must provide either client or all direct initialization parameters")
            self.client = AsyncAzureOpenAIClient(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=api_version,
            )

    def load_model(self):
        return self.client

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    def embed_text(self, text: str) -> List[float]:
        embed = self.client.embeddings.create(
            input=[text],
            model=self.model_name
        )
        return embed.data[0].embedding

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embed = self.client.embeddings.create(
            input=texts,
            model=self.model_name
        )
        return [e.embedding for e in embed.data]

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def a_embed_text(self, text: str) -> List[float]:
        embed = await self.client.embeddings.create(
            input=[text],
            model=self.model_name
        )
        return embed.data[0].embedding

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        async with self.semaphore:
            embed = await self.client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return [e.embedding for e in embed.data]

    def get_model_name(self):
        return f"Azure Embedding Model - {self.model_name}"