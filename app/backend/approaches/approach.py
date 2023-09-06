from abc import ABC, abstractmethod
from typing import Any


class AskApproach(ABC):
    @abstractmethod
    async def run(self, q: str, overrides: dict[str, Any]) -> dict[str, Any]:
        ...
