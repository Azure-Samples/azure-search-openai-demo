from enum import Enum
from typing import Optional
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
