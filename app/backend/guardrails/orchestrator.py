from typing import List
import logging
from openai.types.chat import ChatCompletionMessageParam
from .guardrail import Guardrail
from .datamodels import GuardrailOnErrorAction, GuardrailValidationResult


class GuardrailsOrchestrator:

    def __init__(self,
                 guardrails: List[Guardrail]):

        self.guardrails_list = guardrails

    async def check_guardrails(
        self,
        messages: List[ChatCompletionMessageParam],
    ):
        guardrail_results = []
        action = None
        response_template = None
        has_failed = False

        for guardrail in self.guardrails_list:
            if (
                has_failed
                and not guardrail.run_with_previous_failures
                and not guardrail.run_on_output_with_input_failure
            ):  
                guardrail_validation_result = GuardrailValidationResult.default_skipped(guardrail.name)
                continue

            guardrail_validation_result = await guardrail.validate(messages)
            guardrail_results.append(guardrail_validation_result)

            # modify the message
            if guardrail_validation_result.modified_message:
                messages[-1]["content"] = guardrail_validation_result.modified_message

            if guardrail_validation_result.passed:
                logging.debug(f"Guardrail {guardrail.name} passed.")
                continue

            # determine action to take
            if guardrail.on_error_action == GuardrailOnErrorAction.BLOCK:
                action = GuardrailOnErrorAction.BLOCK
                response_template = guardrail.response_template
                has_failed = True
                break
            elif guardrail.on_error_action == GuardrailOnErrorAction.CONTINUE_WITH_NO_ACTION:
                logging.warning(f"Guardrail {guardrail.name} failed, but continuing with no action.")
                continue
            elif (
                guardrail.on_error_action == GuardrailOnErrorAction.CONTINUE_WITH_RESPONSE_TEMPLATE
                and response_template is None
            ):
                # for now, let others block if needed
                action = GuardrailOnErrorAction.CONTINUE_WITH_RESPONSE_TEMPLATE
                response_template = guardrail.response_template_meta_prompt
                has_failed = True
                continue
            elif guardrail.on_error_action == GuardrailOnErrorAction.CONTINUE_WITH_RESPONSE_TEMPLATE:
                logging.warning(
                    f"Guardrail {guardrail.name} failed, but a previous guardrail already set the response template."
                )
            else:
                logging.warning(
                    f"Guardrail {guardrail.name} failed, action was: {guardrail.on_error_action.value}, no action has been taken."
                )
        logging.debug(f"Guardrail results: {guardrail_results}")
        return guardrail_results, action, response_template

    async def update_chat_history(
        self,
        messages: List[ChatCompletionMessageParam],
    ):
        return_response_immediately = False
        guardrail_results, action, response_template = await self.check_guardrails(messages)

        if action == GuardrailOnErrorAction.CONTINUE_WITH_NO_ACTION:
                    pass
        elif action in {GuardrailOnErrorAction.BLOCK, GuardrailOnErrorAction.TRUNCATE_HISTORY}:
            if action == GuardrailOnErrorAction.TRUNCATE_HISTORY:
                # Keep only the system prompt; TODO: consider few-shot
                messages = [messages[0]]
            messages.append({"role": "assistant", "content": response_template})
            return_response_immediately = True
        return guardrail_results, messages, return_response_immediately
