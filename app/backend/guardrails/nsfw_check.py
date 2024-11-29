from typing import List
from openai.types.chat import ChatCompletionMessageParam
from guardrails.datamodels import GuardrailOnErrorAction, GuardrailValidationResult, GuardrailStates
from guardrails.guardrail_base import GuardrailBase
from transformers import pipeline


class NSFWCheck(GuardrailBase):
    """
    A guardrail that checks for NSFW content in the user's message.
    """

    def __init__(self):
        super().__init__(
            name="nsfw_check",
            error_action=GuardrailOnErrorAction.BLOCK,
            continue_on_failure=False,
            validate_failed_output=True,
        )

    def __post_init__(self):
        # Use object.__setattr__ to set attributes on a frozen dataclass
        object.__setattr__(self, "threshold", 0.7)
        object.__setattr__(self, "model", pipeline("text-classification", model="michellejieli/NSFW_text_classifier"))

    @property
    def template(self) -> str:
        return (
            "I apologize, but it seems that the message contains NSFW content. "
            "Let's keep our conversation appropriate for all audiences. Could you please rephrase "
            "your message?"
        )

    async def validate(
        self,
        messages: List[ChatCompletionMessageParam],
        **kwargs,
    ) -> GuardrailValidationResult:
        """
        Validates the latest message for NSFW content.

        Args:
            messages: List of chat messages, with the latest message to validate

        Returns:
            GuardrailValidationResult indicating whether the message passed or failed
        """
        latest_message = messages[-1]["content"]
        prediction = self.model(latest_message)

        if prediction and prediction[0]["label"] == "NSFW" and prediction[0]["score"] > self.threshold:
            return GuardrailValidationResult(
                guardrail_name=self.name,
                state=GuardrailStates.FAILED,
                message="This text contains NSFW content.",
            )

        return GuardrailValidationResult(
            guardrail_name=self.name,
            state=GuardrailStates.PASSED,
            message="Message passed content filter.",
        )
