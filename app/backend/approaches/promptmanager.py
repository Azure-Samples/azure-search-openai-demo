import json
import pathlib

import prompty
from openai.types.chat import ChatCompletionMessageParam


class PromptManager:

    def load_prompt(self, path: str):
        raise NotImplementedError

    def load_tools(self, path: str):
        raise NotImplementedError

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        raise NotImplementedError


class PromptyManager(PromptManager):

    PROMPTS_DIRECTORY = pathlib.Path(__file__).parent / "prompts"

    def load_prompt(self, path: str):
        return prompty.load(self.PROMPTS_DIRECTORY / path)

    def load_tools(self, path: str):
        return json.loads(open(self.PROMPTS_DIRECTORY / path).read())

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        return prompty.prepare(prompt, data)
