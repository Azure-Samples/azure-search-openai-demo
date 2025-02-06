import json
import pathlib
from dataclasses import dataclass

import prompty
from openai.types.chat import ChatCompletionMessageParam


@dataclass
class RenderedPrompt:
    all_messages: list[ChatCompletionMessageParam]
    system_content: str
    few_shot_messages: list[ChatCompletionMessageParam]
    past_messages: list[ChatCompletionMessageParam]
    new_user_content: str


class PromptManager:

    def load_prompt(self, path: str):
        raise NotImplementedError

    def load_tools(self, path: str):
        raise NotImplementedError

    def render_prompt(self, prompt, data) -> RenderedPrompt:
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

        all_messages: list = prompty.prepare(prompt, data)
        remaining_messages = all_messages.copy()

        system_content = None
        if all_messages[0]["role"] == "system":
            system_content = all_messages[0]["content"]
            remaining_messages.pop(0)
        else:
            raise ValueError("The first message in the prompt must be a system message.")

        new_user_content = None
        if all_messages[-1]["role"] == "user":
            new_user_content = all_messages[-1]["content"]
            remaining_messages.pop(-1)
        else:
            raise ValueError("The last message in the prompt must be a user message.")

        few_shot_messages = []
        past_messages = []
        for user_message, assistant_message in zip(remaining_messages[0::2], remaining_messages[1::2]):
            if user_message["content"].startswith("(EXAMPLE)"):
                user_message["content"] = user_message["content"][9:].lstrip()
                few_shot_messages.extend([user_message, assistant_message])
            else:
                past_messages.extend([user_message, assistant_message])

        return RenderedPrompt(
            all_messages=all_messages,
            system_content=system_content,
            few_shot_messages=few_shot_messages,
            past_messages=past_messages,
            new_user_content=new_user_content,
        )
