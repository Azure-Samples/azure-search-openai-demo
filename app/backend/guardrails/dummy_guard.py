from typing import List

from openai.types.chat import ChatCompletionMessageParam
from .datamodels import GuardrailOnErrorAction, GuardrailValidationResult, GuardrailStates
from .guardrail import Guardrail


class DetectDummy(Guardrail):
    """
    Dummy guardrail to detect profanity in text.
    """

    def __init__(self):
        super().__init__(
            name="Dummy",
            on_error_action=GuardrailOnErrorAction.BLOCK,
            run_with_previous_failures=False,
            run_on_output_with_input_failure=True,
        )
        self.default_stop_list = ["word_a", "word_b", "word_c"]

    @property
    def response_template(self) -> str:
        return "I'm sorry, but I'm unable to respond to that message as it contains word from the stop list."
    
    def predict(self,
                text: str, stop_list: List[str]) -> List[int]:
        if any(word.lower() in text.lower() for word in stop_list):
            return [1]
        return [0]

    async def _validate(
        self,
        messages: List[ChatCompletionMessageParam],
    ) -> GuardrailValidationResult:

        message = messages[-1]["content"]
        prediction = self.predict(message, self.default_stop_list)
        if prediction[0] == 1:
            return GuardrailValidationResult(
                guardrail_name=self.name,
                state=GuardrailStates.FAILED,
                message="This text contains word from the stop list.",
            )
        
        return GuardrailValidationResult(
            guardrail_name=self.name,
            state=GuardrailStates.PASSED,
            message="Guardrail passed",
        )