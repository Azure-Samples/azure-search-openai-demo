from abc import ABC, abstractmethod


class BaseAPIClient(ABC):

    def __init__(self):
        pass

    @abstractmethod
    async def chat_completion(self, *args, **kwargs):
        pass

    @abstractmethod
    async def create_embedding(self, *args, **kwargs):
        pass

    @abstractmethod
    def format_message(self, message: str):
        pass
