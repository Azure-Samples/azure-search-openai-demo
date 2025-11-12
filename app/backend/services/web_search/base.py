from typing import Protocol, List, Dict, Any


class WebSearchProvider(Protocol):
    async def search(self, query: str, top: int = 5) -> List[Dict[str, Any]]:
        ...


