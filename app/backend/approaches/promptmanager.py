import json
import pathlib
from dataclasses import dataclass

import prompty


@dataclass
class RenderedPrompt:
    system_content: str
    few_shot_messages: list[str]
    past_messages: list[str]
    new_user_content: str


class PromptManager:

    def load_prompt(self, path: str):
        raise NotImplementedError

    def load_tools(self, path: str):
        raise NotImplementedError

    def render_prompt(self, prompt, data) -> list:
        raise NotImplementedError


class PromptyManager(PromptManager):

    PROMPTS_DIRECTORY = pathlib.Path(__file__).parent / "prompts"

    def load_prompt(self, path: str):
        return prompty.load(self.PROMPTS_DIRECTORY / path)

    def load_tools(self, path: str):
        return json.loads(open(self.PROMPTS_DIRECTORY / path).read())

    def render_prompt(self, prompt, data) -> RenderedPrompt:
        # Assumes that the first message is the system message, the last message is the user message,
        # and the messages in-between are either examples or past messages.

        messages: list = prompty.prepare(prompt, data)

        system_content = None
        if messages[0]["role"] == "system":
            system_content = messages[0]["content"]
            messages.pop(0)

        new_user_content = None
        if messages[-1]["role"] == "user":
            new_user_content = messages[-1]["content"]
            messages.pop(-1)

        few_shot_messages = []
        past_messages = []
        for user_message, assistant_message in zip(messages[0::2], messages[1::2]):
            if user_message["content"].startswith("(EXAMPLE)"):
                user_message["content"] = user_message["content"][9:].lstrip()
                few_shot_messages.extend([user_message, assistant_message])
            else:
                past_messages.extend([user_message, assistant_message])

        return RenderedPrompt(
            system_content=system_content,
            few_shot_messages=few_shot_messages,
            past_messages=past_messages,
            new_user_content=new_user_content,
        )
