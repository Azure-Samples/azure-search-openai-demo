from abc import abstractmethod

class IChatGptProxy:
    @abstractmethod
    def chat_completion(self, conversations: list(dict[str, str]), temperature:float = 0.7, max_tokens:int = 1024, n:int=1) -> str:
        """
        Generate a chat completion based on the provided conversations.
        Parameters:
        conversations (list[dict[str, str]]): A list of conversation dictionaries.
            Each conversation dictionary should have 'role' and 'content' keys.
        Returns:
        str: The generated chat completion as a string.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the underlying ChatGPT model.
        Returns:
        str: The model name.
        """
        pass

    @abstractmethod
    def get_token_limit(self) -> int:
        """
        Get the token limit for input text imposed by the ChatGPT model.
        Returns:
        int: The token limit.
        """
        pass  