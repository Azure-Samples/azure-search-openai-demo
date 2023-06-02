from abc import abstractmethod, ABC
from typing import Any


class ChatApproach(ABC):
    @abstractmethod
    def run(self, history: list[dict], overrides: dict[str, Any]) -> Any:
        ...


class AskApproach(ABC):
    @abstractmethod
    def run(self, q: str, overrides: dict[str, Any]) -> Any:
        ...
