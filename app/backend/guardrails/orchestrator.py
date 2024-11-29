from typing import List, Tuple, Optional
import logging
import time
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from .guardrail_base import GuardrailBase
from .datamodels import GuardrailOnErrorAction, GuardrailValidationResult, ValidationResult


class GuardrailsOrchestrator:
    """Orchestrates multiple guardrails for message validation"""

    def __init__(self, openai_client: AsyncOpenAI, guardrails: List[GuardrailBase]):
        self.guardrails = guardrails
        self.openai_client = openai_client
        self.logger = logging.getLogger(__name__)

    async def _validate_single_guardrail(
        self, guardrail: GuardrailBase, messages: List[ChatCompletionMessageParam], validation_failed: bool
    ) -> Optional[GuardrailValidationResult]:
        """Validate a single guardrail and return its result"""
        if (
            validation_failed
            and not guardrail.run_with_previous_failures
            and not guardrail.run_on_output_with_input_failure
        ):
            return GuardrailValidationResult.default_skipped(guardrail.name)

        result = await guardrail.validate(messages)
        if result.modified_message:
            messages[-1]["content"] = result.modified_message

        return result

    def _handle_failed_validation(
        self, guardrail: GuardrailBase, current_template: Optional[str]
    ) -> Tuple[GuardrailOnErrorAction, Optional[str], bool]:
        """Handle failed validation and determine appropriate action"""
        match guardrail.error_action:
            case GuardrailOnErrorAction.BLOCK:
                return (GuardrailOnErrorAction.BLOCK, guardrail.template, True)

            case GuardrailOnErrorAction.CONTINUE_WITH_NO_ACTION:
                self.logger.warning(f"Guardrail {guardrail.name} failed, continuing without action")
                return (GuardrailOnErrorAction.CONTINUE_WITH_NO_ACTION, None, False)

            case GuardrailOnErrorAction.CONTINUE_WITH_RESPONSE_TEMPLATE:
                if not current_template:
                    return (guardrail.error_action, guardrail.formatted_template, True)
                self.logger.warning(f"Guardrail {guardrail.name} failed, using existing template")

            case _:
                self.logger.warning(f"Guardrail {guardrail.name} failed with action: {guardrail.error_action.value}")

        return (None, current_template, False)

    async def validate_messages(
        self,
        messages: List[ChatCompletionMessageParam],
    ) -> ValidationResult:
        """Validate messages against all guardrails"""
        validation_results = []
        messages_copy = messages.copy()
        current_action = None
        current_template = None
        validation_failed = False

        for guardrail in self.guardrails:
            result = await self._validate_single_guardrail(guardrail, messages_copy, validation_failed)
            if not result:
                continue

            validation_results.append(result)

            if result.passed:
                self.logger.debug(f"Guardrail {guardrail.name} passed")
                continue

            action, template, failed = self._handle_failed_validation(guardrail, current_template)

            if action:
                current_action = action
                current_template = template
            if failed:
                validation_failed = True
            if action == GuardrailOnErrorAction.BLOCK:
                break

        self.logger.debug(f"Validation results: {validation_results}")
        return ValidationResult(
            results=validation_results, action=current_action, template=current_template, messages=messages_copy
        )

    async def process_chat_history(
        self,
        messages: List[ChatCompletionMessageParam],
    ) -> ValidationResult:
        """Process and update chat history based on validation results"""
        validation = await self.validate_messages(messages)

        if validation.action in {GuardrailOnErrorAction.BLOCK, GuardrailOnErrorAction.TRUNCATE_HISTORY}:
            if validation.action == GuardrailOnErrorAction.TRUNCATE_HISTORY:
                validation.messages = [messages[0]]

            validation.messages.append({"role": "assistant", "content": validation.template})
            validation.immediate_response = True

            async def immediate_response_coroutine():
                return ChatCompletion(
                    id="guardrail_immediate_response",
                    model="manual",
                    created=int(time.time()),
                    object="chat.completion",
                    choices=[
                        Choice(
                            message=ChatCompletionMessage(
                                role="assistant",
                                content=validation.template,
                            ),
                            finish_reason="stop",
                            index=0,
                        )
                    ],
                )

            validation.immediate_response_coroutine = immediate_response_coroutine

        return validation
