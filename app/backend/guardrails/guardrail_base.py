from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import List, ClassVar
from openai.types.chat import ChatCompletionMessageParam
from .datamodels import GuardrailOnErrorAction, GuardrailValidationResult


@dataclass(frozen=False, slots=True)
class GuardrailBase(ABC):
    """
    Base class for implementing security guardrails in chat systems.

    Args:
        name: Identifier for the guardrail
        error_action: Action to take on validation failure
        continue_on_failure: Whether to proceed after previous failures
        validate_failed_output: Whether to validate output after input failure
    """

    name: str
    error_action: GuardrailOnErrorAction
    continue_on_failure: bool = True
    validate_failed_output: bool = True

    # Class-level constants
    TEMPLATE_REQUIRED_ACTIONS: ClassVar[frozenset] = frozenset(
        {
            GuardrailOnErrorAction.CONTINUE_WITH_RESPONSE_TEMPLATE,
            GuardrailOnErrorAction.BLOCK,
            GuardrailOnErrorAction.TRUNCATE_HISTORY,
        }
    )

    ERROR_MESSAGES: ClassVar[dict] = {
        "template": "[{name}] Template implementation required",
        "action_template": "[{name}] Template required for action: {action}",
    }

    def __post_init__(self) -> None:
        """Validates guardrail configuration."""
        if self.needs_template:
            self._verify_template()

    @property
    def needs_template(self) -> bool:
        """Checks if the current error action requires a template."""
        return self.error_action in self.TEMPLATE_REQUIRED_ACTIONS

    def _verify_template(self) -> None:
        """Verifies template implementation when required."""
        try:
            _ = self.template
        except NotImplementedError as e:
            raise NotImplementedError(
                self.ERROR_MESSAGES["action_template"].format(name=self.name, action=self.error_action)
            ) from e

    @property
    @abstractmethod
    def template(self) -> str:
        """Template message for failed validation."""
        raise NotImplementedError(self.ERROR_MESSAGES["template"].format(name=self.name))

    @cached_property
    def formatted_template(self) -> str:
        """Returns formatted error template with context."""
        return f"""
        Guardrail '{self.name}' validation failed.
        Error response:
        ```
        {self.template}
        ```
        """.strip()

    @abstractmethod
    async def validate(self, messages: List[ChatCompletionMessageParam], **kwargs) -> GuardrailValidationResult:
        """
        Validates chat messages against guardrail rules.

        Args:
            messages: Chat messages to validate
            **kwargs: Additional validation parameters

        Returns:
            Validation result with status and any modifications
        """
        pass
