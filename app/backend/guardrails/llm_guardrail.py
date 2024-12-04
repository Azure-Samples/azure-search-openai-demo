from instructor import InstructorClient
from pydantic import BaseModel, Field, Optional
from guardrail_base import GuardrailBase

class LLMGuardrail(GuardrailBase):
    BASE_PROMPT = """
{task_prompt}

{previous_queries}

<LatestQuery>{latest_query}</LatestQuery>
"""

    def __init__(self, instructor_client: InstructorClient, prompt_config: GuardrailPromptConfig):
        self.prompt_config = prompt_config
        self._instructor_client = instructor_client

    def classify(self, query: str) -> LLMGuardrailResponseModel:
        prompt = self.prompt_config.to_prompt()
        # use structured outputs if available
        response = self._instructor_client.regular_openai_call(response_model=LLMGuardrailResponseModel, prompt=prompt)
        return LLMGuardrailResponseModel.model_validate_json(response)


class GuardrailTags:
    EXAMPLES = "Examples"
    EXAMPLE = "Example"
    QUERY = "Query"
    RESULT = "Result"
    EXPLANATION = "Explanation"
    PREVIOUS_QUERIES = "PreviousQueries"
    LATEST_QUERY = "LatestQuery"

class GuardrailExample(BaseModel):
    query: str
    result: str
    explanation: str

    def to_prompt(self) -> str:
        return f"""<{GuardrailTags.EXAMPLE}>
<{GuardrailTags.QUERY}>
{self.query}
<{GuardrailTags.QUERY}/>
<{GuardrailTags.RESULT}>
{self.result}
<{GuardrailTags.RESULT}/>
<{GuardrailTags.EXPLANATION}>
{self.explanation}
<{GuardrailTags.EXPLANATION}/>
</{GuardrailTags.EXAMPLE}>
"""

class GuardrailPromptConfig(BaseModel):
    task_description: str
    examples: list[GuardrailExample]
    additional_context: Optional[str] = None

    def to_prompt(self) -> str:
        prompt = f"""{self.task_description}

<{GuardrailTags.EXAMPLES}>
"""
        for example in self.examples:
            prompt += example.to_prompt()
        prompt += f"""</{GuardrailTags.EXAMPLES}>

"""
        if self.additional_context:
            prompt += f"""<{GuardrailTags.ADDITIONAL_CONTEXT}>
{self.additional_context}
<{GuardrailTags.ADDITIONAL_CONTEXT}/>

"""
        return prompt
    
class OutputLabels:
    PASS = "PASS"
    FAIL = "FAIL"

class LLMGuardrailResponseModel(BaseModel):
    label: OutputLabels = Field(..., description="The label for the query")