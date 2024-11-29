from typing import List
from openai.types.chat import ChatCompletionMessageParam
from guardrails.datamodels import GuardrailOnErrorAction, GuardrailValidationResult, GuardrailStates
from guardrails.guardrail_base import GuardrailBase
from fuzzysearch import find_near_matches


class BanListCheck(GuardrailBase):
    """
    A guardrail that checks for banned words in the user's message using fuzzy search.
    """

    def __init__(self, banned_words: List[str], max_l_dist: int = 1):
        super().__init__(
            name="ban_list_check",
            error_action=GuardrailOnErrorAction.BLOCK,
            continue_on_failure=False,
            validate_failed_output=True,
        )
        self._banned_words = banned_words
        self._max_l_dist = max_l_dist

    @property
    def template(self) -> str:
        return (
            "I apologize, but it seems that the message contains prohibited words. "
            "Please remove any inappropriate language and try again."
        )

    async def validate(
        self,
        messages: List[ChatCompletionMessageParam],
        **kwargs,
    ) -> GuardrailValidationResult:
        """
        Validates the latest message against a list of banned words.

        Args:
            messages: List of chat messages, with the latest message to validate

        Returns:
            GuardrailValidationResult indicating whether the message passed or failed
        """
        latest_message = messages[-1]["content"]
        spaceless_value = latest_message.replace(" ", "").lower()
        spaceless_index_map = [(char, idx) for idx, char in enumerate(latest_message) if char != " "]

        all_matches = []
        for banned_word in self._banned_words:
            spaceless_banned_word = banned_word.replace(" ", "").lower()
            matches = find_near_matches(spaceless_banned_word, spaceless_value, max_l_dist=self._max_l_dist)
            all_matches.extend(matches)

        if all_matches:
            error_spans = []
            fix_value = latest_message
            for match in all_matches:
                actual_start = spaceless_index_map[match.start][1]
                actual_end = spaceless_index_map[match.end - 1][1]
                triggering_text = latest_message[actual_start:actual_end]
                fix_value = fix_value.replace(triggering_text, "")
                error_spans.append(
                    {
                        "start": actual_start,
                        "end": actual_end,
                        "reason": f"Found match with banned word '{match.matched}' in '{triggering_text}'",
                    }
                )

            return GuardrailValidationResult(
                guardrail_name=self.name,
                state=GuardrailStates.FAILED,
                message="Output contains banned words.",
                error_spans=error_spans,
                fix_value=fix_value,
            )

        return GuardrailValidationResult(
            guardrail_name=self.name,
            state=GuardrailStates.PASSED,
            message="Message passed content filter.",
        )
