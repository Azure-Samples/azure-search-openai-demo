import json
import pathlib
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)


class PromptManager:
    """Builds OpenAI chat completion messages from Jinja2 templates."""

    PROMPTS_DIRECTORY = pathlib.Path(__file__).parent / "prompts"

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(self.PROMPTS_DIRECTORY),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_system_prompt(
        self, template_path: str, template_variables: dict[str, Any]
    ) -> ChatCompletionSystemMessageParam:
        """Build a single system message. Use for simple prompts like query rewrite.

        Args:
            template_path: Path to the system message template file
            template_variables: Dictionary of variables to pass to the template

        Returns:
            A system message
        """
        content = self.env.get_template(template_path).render(**template_variables).strip()
        return {"role": "system", "content": content}

    def build_user_prompt(
        self,
        template_path: str,
        template_variables: dict[str, Any],
        image_sources: list[str] | None = None,
    ) -> ChatCompletionUserMessageParam:
        """Build a single user message with optional images.

        Args:
            template_path: Path to the user message template file
            template_variables: Dictionary of variables to pass to the template
            image_sources: Optional list of image URLs to include in the message

        Returns:
            A user message
        """
        user_text = self.env.get_template(template_path).render(**template_variables).strip()
        if image_sources:
            user_content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
            for image in image_sources:
                user_content.append({"type": "image_url", "image_url": {"url": image, "detail": "auto"}})
            return cast(ChatCompletionUserMessageParam, {"role": "user", "content": user_content})
        return {"role": "user", "content": user_text}

    def build_conversation(
        self,
        system_template_path: str,
        system_template_variables: dict[str, Any],
        user_template_path: str,
        user_template_variables: dict[str, Any],
        user_image_sources: list[str] | None = None,
        past_messages: list[ChatCompletionMessageParam] | None = None,
    ) -> list[ChatCompletionMessageParam]:
        """Build a full conversation with system, history, and user message.

        Args:
            system_template_path: Path to the system message template file
            system_template_variables: Dictionary of variables to pass to the system template
            user_template_path: Path to the user message template file
            user_template_variables: Dictionary of variables to pass to the user template
            user_image_sources: Optional list of image URLs to include in the user message
            past_messages: Optional list of past messages to include as conversation history

        Returns:
            A list of ChatCompletionMessageParam messages
        """
        messages: list[ChatCompletionMessageParam] = []

        # System message
        messages.append(self.build_system_prompt(system_template_path, system_template_variables))

        # Past messages (conversation history)
        for msg in past_messages or []:
            messages.append(cast(ChatCompletionMessageParam, msg))

        # User message (with optional images)
        messages.append(self.build_user_prompt(user_template_path, user_template_variables, user_image_sources))

        return messages

    def load_tools(self, path: str) -> list[ChatCompletionToolParam]:
        """Load tools from a JSON file."""
        with open(self.PROMPTS_DIRECTORY / path) as f:
            return cast(list[ChatCompletionToolParam], json.load(f))
