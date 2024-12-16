import instructor
from openai import AsyncAzureOpenAI 
from pydantic import BaseModel, Field
from typing import Optional
from guardrails.guardrail_base import GuardrailBase
from guardrails.datamodels import GuardrailOnErrorAction

class GuardrailTags:
    EXAMPLES = "Examples"
    EXAMPLE = "Example"
    QUERY = "Query"
    RESULT = "Result"
    EXPLANATION = "Explanation"
    CONTENT = "Content"

class GuardrailExample(BaseModel):
    query: str
    result: str
    explanation: str

    def to_prompt(self) -> str:
        return f"""<{GuardrailTags.EXAMPLE}>
<{GuardrailTags.QUERY}>{self.query}</{GuardrailTags.QUERY}>
<{GuardrailTags.RESULT}>{self.result}</{GuardrailTags.RESULT}>
<{GuardrailTags.EXPLANATION}>{self.explanation}</{GuardrailTags.EXPLANATION}>
</{GuardrailTags.EXAMPLE}>"""
    
class OutputLabels:
    PASS = "PASS"
    FAIL = "FAIL"

class LLMGuardrailResponseModel(BaseModel):
    label: str = Field(..., description="The result of the guardrail check (PASS/FAIL)")
    explanation: Optional[str] = Field(None, description="Explanation for the reasoning")

class GuardrailPromptConfig(BaseModel):
    task_description: str
    examples: list[GuardrailExample]
    additional_context: Optional[str] = None

    def to_prompt(self) -> str:
        prompt = f"""{self.task_description}
<{GuardrailTags.EXAMPLES}>"""
        for example in self.examples:
            prompt += example.to_prompt()
        prompt += f"""</{GuardrailTags.EXAMPLES}>"""
        if self.additional_context:
            prompt += f"\n{self.additional_context}"
        return prompt

class LLMGuardrail(GuardrailBase):
    BASE_PROMPT = """{base_prompt}
<{content_tag}>{message}</{content_tag}>"""

    def __init__(self, prompt_config: GuardrailPromptConfig,
                 error_action: GuardrailOnErrorAction,
                 temperature: float = 0):
        super().__init__(
            name="llm_guardrail",
            error_action=error_action,
            continue_on_failure=False,
            validate_failed_output=True
        )
        self.prompt_config = prompt_config
        self.llm_client = None
        self.model_name = None
        self._instructor_client = None
        self.temperature = temperature

    def load(self, client: AsyncAzureOpenAI,
                       model_name: str):
        self.llm_client = client
        self.model_name = model_name
        self._instructor_client = instructor.patch(client)

    @property
    def template(self) -> str:
        return "Content validation failed. Please try again."

    async def classify(self, message: str) -> LLMGuardrailResponseModel:
        base_prompt = self.prompt_config.to_prompt()
        prompt = self.BASE_PROMPT.format(
            base_prompt=base_prompt,
            content_tag=GuardrailTags.CONTENT,
            message=message
        )
        try:
            response = await self._instructor_client.chat.completions.create(
                model=self.model_name,
                response_model=LLMGuardrailResponseModel,
                messages=[{"role": "system", "content": prompt}],
                temperature=self.temperature
            )
            return response
        except Exception as e:
            print("Error during API call:", e)
            return LLMGuardrailResponseModel(label=OutputLabels.FAIL, 
                                           explanation="Error in classify")



