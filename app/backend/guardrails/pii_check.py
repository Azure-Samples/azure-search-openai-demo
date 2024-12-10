from typing import List, Union
from openai.types.chat import ChatCompletionMessageParam
from guardrails.datamodels import GuardrailOnErrorAction, GuardrailValidationResult, GuardrailStates
from guardrails.guardrail_base import GuardrailBase
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import difflib


class PIICheck(GuardrailBase):
    """
    A guardrail that checks for PII in the user's message.
    """

    PII_ENTITIES_MAP = {
        "pii": [
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "DOMAIN_NAME",
            "IP_ADDRESS",
            "DATE_TIME",
            "LOCATION",
            "PERSON",
            "URL",
        ],
        "spi": [
            "CREDIT_CARD",
            "CRYPTO",
            "IBAN_CODE",
            "NRP",
            "MEDICAL_LICENSE",
            "US_BANK_NUMBER",
            "US_DRIVER_LICENSE",
            "US_ITIN",
            "US_PASSPORT",
            "US_SSN",
        ],
    }

    def __init__(self, pii_entities: Union[str, List[str], None] = "pii"):
        super().__init__(
            name="pii_check",
            error_action=GuardrailOnErrorAction.BLOCK,
            continue_on_failure=False,
            validate_failed_output=True,
        )
        self.pii_entities = pii_entities
        self.pii_analyzer = AnalyzerEngine()
        self.pii_anonymizer = AnonymizerEngine()

    @property
    def template(self) -> str:
        return (
            "It seems that the message contains sensitive information. "
            "Please remove any personal data and try again."
        )

    async def validate(
        self,
        messages: List[ChatCompletionMessageParam],
        **kwargs,
    ) -> GuardrailValidationResult:
        """
        Validates the latest message for PII content.

        Args:
            messages: List of chat messages, with the latest message to validate

        Returns:
            GuardrailValidationResult indicating whether the message passed or failed
        """
        latest_message = messages[-1]["content"]
        entities_to_filter = self._get_entities_to_filter(kwargs.get("metadata", {}))

        anonymized_text = self.get_anonymized_text(latest_message, entities_to_filter)
        if anonymized_text == latest_message:
            return GuardrailValidationResult(
                guardrail_name=self.name,
                state=GuardrailStates.PASSED,
                message="Message passed content filter.",
            )

        error_spans = self._get_error_spans(latest_message, anonymized_text)

        return GuardrailValidationResult(
            guardrail_name=self.name,
            state=GuardrailStates.FAILED,
            message="The message contains PII.",
            error_spans=error_spans,
            fix_value=anonymized_text,
        )

    def _get_entities_to_filter(self, metadata: dict) -> List[str]:
        pii_entities = metadata.get("pii_entities", self.pii_entities)
        if isinstance(pii_entities, str):
            entities_to_filter = self.PII_ENTITIES_MAP.get(pii_entities)
            if entities_to_filter is None:
                raise ValueError(f"`pii_entities` must be one of {list(self.PII_ENTITIES_MAP.keys())}")
        elif isinstance(pii_entities, list):
            entities_to_filter = pii_entities
        else:
            raise ValueError("`pii_entities` must be a string or a list of strings.")
        return entities_to_filter

    def get_anonymized_text(self, text: str, entities: List[str]) -> str:
        results = self.pii_analyzer.analyze(text=text, entities=entities, language="en")
        anonymized_text = self.pii_anonymizer.anonymize(text=text, analyzer_results=results).text
        return anonymized_text

    def _get_error_spans(self, original: str, anonymized: str) -> List[dict]:
        differ = difflib.Differ()
        diffs = list(differ.compare(original, anonymized))
        start_range = None
        diff_ranges = []
        curr_index_in_original = 0
        for diff in diffs:
            if start_range is not None and diff[0] != "-":
                diff_ranges.append((start_range, curr_index_in_original))
                start_range = None
            if diff[0] == "-":
                if start_range is None:
                    start_range = curr_index_in_original
            if diff[0] != "+":
                curr_index_in_original += 1

        error_spans = []
        for diff_range in diff_ranges:
            error_spans.append(
                {
                    "start": diff_range[0],
                    "end": diff_range[1],
                    "reason": f"PII detected in {original[diff_range[0]:diff_range[1]]}",
                }
            )
        return error_spans
