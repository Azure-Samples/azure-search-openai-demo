from abc import ABC, abstractmethod
from typing import Optional, List
from openai.types.chat import ChatCompletionMessageParam
from .datamodels import GuardrailOnErrorAction, GuardrailValidationResult


"""
Base class for guardrails
"""


class Guardrail(ABC):
    def __init__(
        self,
        name: str,
        on_error_action: GuardrailOnErrorAction,
        run_with_previous_failures: bool,
        run_on_output_with_input_failure: bool,
    ):
        self._name = name
        self._run_with_previous_failures = run_with_previous_failures
        self._run_on_output_with_input_failure = run_on_output_with_input_failure
        self._on_error_action = on_error_action

        # check response template is implemented
        if self._on_error_action in [
            GuardrailOnErrorAction.CONTINUE_WITH_RESPONSE_TEMPLATE,
            GuardrailOnErrorAction.BLOCK,
            GuardrailOnErrorAction.TRUNCATE_HISTORY,
        ]:
            _ = self.response_template

    @property
    def run_with_previous_failures(self) -> bool:
        return self._run_with_previous_failures

    @property
    def run_on_output_with_input_failure(self) -> bool:
        return self._run_on_output_with_input_failure

    @property
    def name(self) -> str:
        return self._name

    @property
    def on_error_action(self) -> GuardrailOnErrorAction:
        return self._on_error_action

    @property
    def response_template(self) -> str:
        raise NotImplementedError(
            f"[{self.name}] response_template must be implemented"
        )

    @property
    def response_template_meta_prompt(self) -> str:
        return f"""The {self.name} guardrail has failed.
                    Response template:
                    ```
                    {self.response_template}
                    ```
                """

    @abstractmethod
    async def _validate(
        self,
        messages: List[ChatCompletionMessageParam],
    ) -> GuardrailValidationResult:
        pass

    async def validate(
        self,
        messages: List[ChatCompletionMessageParam],
        *args,
        **kwargs,
    ) -> GuardrailValidationResult:
        try:
            guardrail_result = await self._validate(messages, *args, **kwargs)
            return guardrail_result
        except Exception as e:
            raise e
