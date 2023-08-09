from abc import ABC, abstractmethod
from typing import Any


class ChatApproach(ABC):
    @abstractmethod
    async def run(self, history: list[dict], overrides: dict[str, Any]) -> Any:
        ...


class AskApproach(ABC):
    @abstractmethod
    async def run(self, q: str, overrides: dict[str, Any]) -> Any:
        ...
