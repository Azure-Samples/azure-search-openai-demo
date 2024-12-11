from openai import AsyncAzureOpenAI 
from typing import List
from openai.types.chat import ChatCompletionMessageParam
from guardrails.datamodels import GuardrailOnErrorAction, GuardrailValidationResult, GuardrailStates
from .llm_guardrail import (
    LLMGuardrail, 
    GuardrailPromptConfig, 
    GuardrailExample, 
    OutputLabels
)

class OutputContentCheck(LLMGuardrail):
    """A guardrail that validates the assistant's output content."""

    def __init__(self):
        prompt_config = GuardrailPromptConfig(
            task_description="""Evaluate if the response meets ALL criteria:
1. Stays within Government GPT's purpose as a NZ government small business services assistant
2. Contains only logical information
3. Avoids speculation or unrealistic promises and logical reasoning
4. Maintains professional tone
5. Excludes harmful, violent, or inappropriate content
6. Uses proper citations from provided sources
7. Doesn't make eligibility determinations
8. Doesn't provide personal advice
Return PASS if all criteria are met, otherwise return FAIL. Also return your reasoning explanation""",
            examples=[
                GuardrailExample(
                    query="According to [business.govt.nz], small businesses can apply for the Regional Business Partner Network programme to access business advice and mentoring services.",
                    result=OutputLabels.PASS,
                    explanation="Valid: Uses citations, stays within scope, provides factual information"
                ),
                GuardrailExample(
                    query="I guarantee your business will succeed if you follow these steps! Here's a creative story about a business owner...",
                    result=OutputLabels.FAIL,
                    explanation="Invalid: Makes unrealistic promises, includes speculation"
                ),
                GuardrailExample(
                    query="Based on your situation, you are definitely eligible for the grant and will receive $50,000.",
                    result=OutputLabels.FAIL,
                    explanation="Invalid: Makes eligibility determinations and specific promises"
                )
            ]
        )
        super().__init__(prompt_config)

    @property
    def template(self) -> str:
        return "I apologize, but question needs to be rephrased to better align with my purpose as a government business services assistant. Please ask your question in different manner."

    async def validate(
        self,
        messages: List[ChatCompletionMessageParam],
        **kwargs,
    ) -> GuardrailValidationResult:
        """Validates the assistant's response content."""
        latest_message = messages[-1]["content"]
        if not isinstance(latest_message, str):
            return GuardrailValidationResult(
                guardrail_name="output_content_check",
                state=GuardrailStates.FAILED,
                message="Invalid message format"
            )
        try:
            result = await self.classify(latest_message)
            return GuardrailValidationResult(
                guardrail_name="output_content_check",
                state=GuardrailStates.PASSED if result.label == OutputLabels.PASS else GuardrailStates.FAILED,
                message=result.explanation or "Content validation failed"
            )
        except Exception as e:
            return GuardrailValidationResult(
                guardrail_name="output_content_check",
                state=GuardrailStates.FAILED,
                message=f"Error validating content: {str(e)}"
            ) 