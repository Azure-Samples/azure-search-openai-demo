from typing import List, Optional
from enum import Enum
from dataclasses import dataclass
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field


class GuardrailStates(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GuardrailOnErrorAction(Enum):
    BLOCK = "block"
    CONTINUE_WITH_NO_ACTION = "continue_with_no_action"
    TRUNCATE_HISTORY = "truncate_history"
    CONTINUE_WITH_RESPONSE_TEMPLATE = "continue_with_response_template"


class GuardrailValidationResult(BaseModel):
    # todo: add name validation
    guardrail_name: str = Field(..., description="The name of the guardrail")
    context: list[dict] = Field([], description="The context to use for the guardrail")
    error_message: Optional[str] = Field(None, description="The error message to use if the guardrail failed")
    modified_message: Optional[str] = Field(None, description="The modified message")
    state: GuardrailStates = Field(GuardrailStates.FAILED, description="The state of the guardrail")

    @property
    def skipped(self) -> bool:
        return self.state == GuardrailStates.SKIPPED

    @property
    def passed(self) -> bool:
        return self.state == GuardrailStates.PASSED

    @property
    def failed(self) -> bool:
        return self.state == GuardrailStates.FAILED

    @staticmethod
    def default_skipped(guardrail_name: str) -> "GuardrailValidationResult":
        return GuardrailValidationResult(
            guardrail_name=guardrail_name,
            context=[],
            state=GuardrailStates.SKIPPED,
        )


@dataclass
class ValidationResult:
    """Container for validation results"""

    results: List[GuardrailValidationResult]
    messages: List[ChatCompletionMessageParam]
    action: Optional[GuardrailOnErrorAction] = None
    template: Optional[str] = None
    immediate_response: bool = False
