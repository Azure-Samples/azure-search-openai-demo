from typing import List
from openai.types.chat import ChatCompletionMessageParam
from profanity_check import predict
from .datamodels import GuardrailOnErrorAction, GuardrailValidationResult, GuardrailStates
from .guardrail_base import GuardrailBase


class ProvanityCheck(GuardrailBase):
    """
    A guardrail that checks for profanity in the user's message.
    """

    def __init__(self):
        super().__init__(
            name="profanity_check",
            error_action=GuardrailOnErrorAction.BLOCK,
            continue_on_failure=False,
            validate_failed_output=True,
        )

    @property
    def template(self) -> str:
        return (
            "I apologize, but it seems that the message contains inappropriate content. "
            "Let's keep our conversation respectful and friendly. Could you please rephrase "
            "your message?"
        )

    async def validate(
        self,
        messages: List[ChatCompletionMessageParam],
        **kwargs,
    ) -> GuardrailValidationResult:
        """
        Validates the latest message against prohibited words.

        Args:
            messages: List of chat messages, with the latest message to validate

        Returns:
            GuardrailValidationResult indicating whether the message passed or failed
        """
        latest_message = messages[-1]["content"]
        prediction = predict([latest_message])

        if prediction[0] == 1:
            return GuardrailValidationResult(
                guardrail_name=self.name,
                state=GuardrailStates.FAILED,
                message="This text contains profanity.",
            )

        return GuardrailValidationResult(
            guardrail_name=self.name,
            state=GuardrailStates.PASSED,
            message="Message passed content filter.",
        )
