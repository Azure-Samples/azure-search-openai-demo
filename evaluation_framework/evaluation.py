"""
LLM Evaluation Script using deepeval metrics.
Evaluates LLM responses for various quality metrics including context precision,
recall, relevancy, faithfulness, and legal risk assessment.
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
from quart import Quart
from dotenv import load_dotenv

from deepeval import evaluate
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from models import ConfigLoader, ModelFactory
from system_rag import RAG
from utils import read_json, save_results

load_dotenv()

class RAGEvaluator:
    """Handles evaluation of RAG system responses"""
    
    def __init__(self,
                 config,
                 app: Optional[Quart] = None):
        """
        Initialize the Evaluator with the provided configuration and evaluation data.
        """
        self.config = config
        self.results_path = config.paths["eval_results"]
        self.custom_metrics = config.paths["custom_metrics"]
        self.max_concurrent = config.max_concurrent
        self.throttle_value = config.throttle_value
        self.app = app
        # Initialize configuration
        if self.app:
            self.llm_model = self.create_model_from_app_config(self.app)
        else:
            self.llm_model = self.create_llm_model()

    async def prepare_eval_data(self,
                                eval_data: List[Dict],
                                rag_system: RAG,
                                save_path: Optional[Path] = None,
                                output_guard: bool = False) -> List[Dict]:
        """Process goldens and return evaluation data"""
        # Process all questions in one batch
        questions = [eval_case["input"] for eval_case in eval_data]
        answers = await rag_system.ask_questions(questions)
        # Update eval_data_list with results
        for i, eval_case in enumerate(eval_data):
            # if answer was blocked by input guard, "results" will be a dict
            # check if results is a list
            _answer = answers["results"][i]["message"]["content"]
            try:
                _context = answers["results"][i]["context"]['data_points']["text"]
            except:
                _context = None
            eval_case["actual_output"] = _answer
            # if context is not found, use the context from the eval_case
            eval_case["retrieval_context"] = _context or eval_case["context"]
        print("user answers prepared")
        if output_guard:
            assistant_answers = [i["actual_output"] for i in eval_data]
            output_guard_answers = await rag_system.ask_questions(assistant_answers, assistant_role=True)
            for i, eval_case in enumerate(eval_data):
                eval_case["actual_output"] = output_guard_answers["results"][i]["message"]["content"]
        print("output guard answers prepared")
        if save_path:
            with open(save_path, "w") as f:
                json.dump(eval_data, f)
        return eval_data
    
    def prepare_goldens(self, goldens: List[Dict]) -> List[Dict]:
        """Prepare goldens for evaluation"""
        eval_data_list = []
        for golden in goldens:
            eval_data = {
                "input": golden["input"],
                "expected_output": golden["expected_output"],
                "context": golden["context"]
            }
            eval_data_list.append(eval_data)
        return eval_data_list
    
    async def _evaluate(self, eval_data: List[Dict]) -> None:
        """
        Run evaluation on the provided test cases.
        eval_data: List of evaluation data
        """
        custom_metrics = read_json(self.custom_metrics)
        metrics = self.create_metrics(self.llm_model, custom_metrics)

        test_cases = [LLMTestCase(**test_case) for test_case in eval_data]

        # Run evaluation
        results = evaluate(
            test_cases=test_cases,
            metrics=metrics,
            throttle_value=self.throttle_value,
            max_concurrent=self.max_concurrent,
            write_cache=False
        )
        # Save results
        if self.results_path:
            save_results(results, self.results_path)

        return results
    
    def load_test_cases(self, test_file: str) -> List[Dict]:
        """Load test cases from a JSON file"""
        test_cases = read_json(test_file)["test_cases"]
        return test_cases
    
    def prepare_tests(self, test_cases: List[Dict]) -> None:
        """Run tests on the provided test cases"""
        custom_metrics = read_json(self.custom_metrics)
        metrics = self.create_metrics(self.llm_model, custom_metrics)
        
        test_cases = [LLMTestCase(**test_case) for test_case in test_cases]
        return test_cases, metrics

    @staticmethod
    def create_llm_model() -> DeepEvalBaseLLM:
        llm_config = ConfigLoader.load_llm_config()
        llm_model = ModelFactory.create_llm_model(llm_config)
        return llm_model

    @staticmethod
    def create_model_from_app_config(current_app):
        llm_model, _ = ModelFactory.from_app_config(current_app)
        return llm_model

    @staticmethod
    def create_metrics(eval_model: DeepEvalBaseLLM,
                      custom_metrics: Optional[Dict] = []) -> List:
        """Create a list of evaluation metrics."""
        default_metrics = [
            ContextualPrecisionMetric(model=eval_model, include_reason=False),
            ContextualRecallMetric(model=eval_model, include_reason=False),
            ContextualRelevancyMetric(model=eval_model, include_reason=False),
            AnswerRelevancyMetric(model=eval_model, include_reason=False),
            FaithfulnessMetric(model=eval_model, include_reason=False),
        ]
        if not custom_metrics:
            return default_metrics
        
        if "metrics" not in custom_metrics:
            raise ValueError("custom_metrics must contain 'metrics' key")
            
        if not isinstance(custom_metrics["metrics"], list):
            raise ValueError("custom_metrics['metrics'] must be a list")

        # Create custom metrics
        metrics = []
        for metric in custom_metrics["metrics"]:
            try:
                metric_object = GEval(
                    model=eval_model,
                    name=metric["name"],
                    criteria=metric["description"],
                    evaluation_params=[LLMTestCaseParams.INPUT,
                                    LLMTestCaseParams.ACTUAL_OUTPUT]
                )
                metrics.append(metric_object)
            except Exception as e:
                raise ValueError(f"Error creating metric {metric['name']}: {str(e)}") from e
        return default_metrics + metrics