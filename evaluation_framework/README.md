# RAG System Evaluation Framework

This framework provides tools for evaluating RAG (Retrieval-Augmented Generation) system responses using various metrics.

## Structure

- `test_file.py` - Test runner for evaluating RAG responses
- `run_evaluation.py` - Complete evaluation pipeline
- `eval_data/` - Test cases and results
- `system_rag.py` - RAG system implementation
- `evaluation.py` - Core evaluation logic
- `eval_config.json` - Configuration settings
- `llm_wrapper.py` - OpenAI model wrapper for DeepEval

## Running Tests

The framework provides two main ways to run evaluations:

### 1. Running Test Cases (`test_file.py`)

This runs predefined test cases and compares RAG responses against expected outputs: 

bash
deepeval test run test_file.py
```

The test file runs two types of tests:
- `test_dummy_responses`: Validates expected outputs against metrics
- `test_rag_responses`: Tests actual RAG system responses

### 2. Running Full Evaluation (`run_evaluation.py`)

This runs the complete evaluation pipeline:

```bash
python run_evaluation.py
```

Features:
- Generates synthetic test data from contexts
- Evaluates RAG responses
- Processes both synthetic and user-defined test cases
- Saves results to `eval_data/results.json`

## Test Cases Structure

Test cases are defined in `eval_data/test_cases.json`:

```json
{
    "test_cases": [
        {
            "input": "question text",
            "expected_output": "expected answer",
            "context": ["relevant context"],
            "retrieval_context": ["retrieved context"]
        }
    ]
}
```

## Evaluation Metrics

The framework uses DeepEval metrics:
- Contextual Precision
- Contextual Recall
- Contextual Relevancy
- Answer Relevancy
- Faithfulness
- Correctness (GEval)

## Configuration

### Config Files
- `eval_config.json`: Main configuration
- Custom metrics configuration
- Test case definitions

## RAG System

The RAG system (`system_rag.py`) provides:
- emulating GovGPT setup

## Results

Evaluation results are saved in JSON format with:
- Individual test case results
- Metric scores and thresholds
- Detailed evaluation logs
- Success/failure status

## Development Notes

### Async Handling
- Uses `asyncio` for async operations
- Requires proper session cleanup
- Implements concurrent request limiting

### Testing Best Practices
- Separate dummy and RAG tests
- Clear test case identification
- Proper resource cleanup
- Metric threshold configuration

### Known Issues
- Session cleanup warnings may appear
- Requires proper async context management
- May need throttling for large test sets

## Dependencies

- Python 3.8+
- pytest
- deepeval
- aiohttp
- Azure OpenAI
- Quart

This README provides comprehensive documentation of the evaluation framework's features, usage, and implementation details. Let me know if you need any section expanded or clarified.