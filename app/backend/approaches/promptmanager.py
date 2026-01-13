import json
import pathlib
from dataclasses import dataclass
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)


class PromptManager:

    def load_prompt(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def load_tools(self, path: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def render_prompt(self, prompt: Any, data: dict[str, Any]) -> list[ChatCompletionMessageParam]:
        raise NotImplementedError


@dataclass
class Jinja2Prompt:
    """A prompt that consists of templates for system message and optional user message."""

    system_template_path: str
    user_template_path: str | None = None
    include_past_messages_as_entries: bool = True
    """If True, past_messages from data are added as separate message entries before the user message."""


class Jinja2PromptManager(PromptManager):
    """Prompt manager that uses Jinja2 templates to render prompts."""

    PROMPTS_DIRECTORY = pathlib.Path(__file__).parent / "prompts"

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(self.PROMPTS_DIRECTORY),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def load_prompt(
        self,
        system_path: str,
        user_path: str | None = None,
        include_past_messages_as_entries: bool = True,
    ) -> Jinja2Prompt:
        """Load a prompt from Jinja2 template files.

        Args:
            system_path: Path to the system message template file
            user_path: Optional path to the user message template file
            include_past_messages_as_entries: If True, past_messages from data are added as separate
                message entries before the user message. Set to False if past_messages should only be
                available for template rendering (e.g., for query rewrite prompts).

        Returns:
            A Jinja2Prompt object containing the template paths
        """
        return Jinja2Prompt(
            system_template_path=system_path,
            user_template_path=user_path,
            include_past_messages_as_entries=include_past_messages_as_entries,
        )

    def load_tools(self, path: str) -> list[dict[str, Any]]:
        """Load tools from a JSON file."""
        with open(self.PROMPTS_DIRECTORY / path) as f:
            return json.load(f)

    def render_prompt(self, prompt: Jinja2Prompt, data: dict[str, Any]) -> list[ChatCompletionMessageParam]:
        """Render a prompt using Jinja2 templates.

        Args:
            prompt: A Jinja2Prompt object containing template paths
            data: Dictionary of variables to pass to the templates

        Returns:
            A list of ChatCompletionMessageParam messages
        """
        messages: list[ChatCompletionMessageParam] = []

        # Render system message
        system_template = self.env.get_template(prompt.system_template_path)
        system_content = system_template.render(**data).strip()
        system_msg: ChatCompletionSystemMessageParam = {"role": "system", "content": system_content}
        messages.append(system_msg)

        # Add past messages if provided (for chat history in chat_answer prompts)
        # This should come before the final user message
        if prompt.user_template_path and prompt.include_past_messages_as_entries:
            past_messages = data.get("past_messages", [])
            for msg in past_messages:
                messages.append(cast(ChatCompletionMessageParam, {"role": msg["role"], "content": msg["content"]}))

        # Render user message if a user template is provided
        if prompt.user_template_path:
            user_template = self.env.get_template(prompt.user_template_path)
            user_content = user_template.render(**data).strip()
            final_user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_content}
            messages.append(final_user_msg)

        return messages
