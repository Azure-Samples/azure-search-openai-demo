# ----------------------------------------------
# Evaluate Target Application (Azure Evaluation SDK)
# Evaluates the actual RAG application backend API
# Following the pattern from evaluate.py sample
# Uses Azure AI Foundry project for results upload
# ----------------------------------------------

import os
import pandas as pd
import requests
from pathlib import Path
from typing import TypedDict
from pprint import pprint

# ----------------------------------------------
# 1. Define Target Function to Query RAG App
# ----------------------------------------------

class RagResponse(TypedDict):
    """Response structure from RAG application evaluation."""
    response: str
    context: str

def evaluate_rag_application(question: str) -> RagResponse:
    """
    Target function that calls the RAG application backend API.
    This function will be evaluated by the Azure AI evaluation SDK.
    
    Args:
        question: The user question to ask the RAG application
        
    Returns:
        RagResponse with response and context for evaluation
    """
    # Read BACKEND_URL from environment each time to support multiprocessing
    backend_url = os.getenv("BACKEND_URI", "http://localhost:50505")
    
    try:
        # Call the /chat endpoint of the RAG application
        response = requests.post(
            f"{backend_url}/chat",
            json={
                "messages": [{"content": question, "role": "user"}],
                "context": {
                    "overrides": {
                        "retrieval_mode": "hybrid",
                        "semantic_ranker": True,
                        "semantic_captions": False,
                        "top": 3,
                        "suggest_followup_questions": False,
                    }
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the answer and context from the response
        answer = result.get("message", {}).get("content", "")
        data_points = result.get("context", {}).get("data_points", {}).get("text", [])
        
        # Format context as string for groundedness evaluation
        context = "\n\n".join(data_points) if data_points else ""
        
        return RagResponse(
            response=answer,
            context=context
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling RAG application: {e}")
        return RagResponse(
            response=f"Error: {str(e)}",
            context=""
        )
# ----------------------------------------------
# 2. Run the Evaluation
#    View Results Locally (Saved as JSONL)
#    Upload Results to AI Foundry Portal
# ----------------------------------------------
# Evaluation must be called inside of __main__, not on import
if __name__ == "__main__":
    import contextlib
    import multiprocessing
    from azure.identity import DefaultAzureCredential
    from azure.ai.evaluation import evaluate
    from azure.ai.evaluation import RelevanceEvaluator, GroundednessEvaluator
    from azure.ai.evaluation import AzureOpenAIModelConfiguration
    from dotenv_azd import load_azd_env
    
    load_azd_env()
    
    BACKEND_URL = os.getenv("BACKEND_URI", "http://localhost:50505")
    
    # Configure Azure AI project for uploading results to AI Foundry
    # New Foundry projects without workspace use the project endpoint URL directly
    azure_ai_project = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    
    # Define evaluator model configuration
    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT"),
        api_version="2024-08-01-preview",
    )
    
    # Initialize evaluators
    relevance_eval = RelevanceEvaluator(model_config)
    groundedness_eval = GroundednessEvaluator(model_config)
    
    # Workaround for multiprocessing issue on linux
    with contextlib.suppress(RuntimeError):
        multiprocessing.set_start_method("spawn", force=True)
    
    # Check if backend is accessible
    try:
        health_check = requests.get(f"{BACKEND_URL}/", timeout=5)
        print(f"✅ Backend is accessible at {BACKEND_URL}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Warning: Cannot connect to backend at {BACKEND_URL}")
        print(f"   Make sure the backend is started. Error: {e}")
        print(f"   Rerun script since container might be idle.  Rerun no more than 5 times.")
        exit(1)
    
    # Define the path to evaluation data
    # You can use your existing data file or create a new one
    data_path = Path("evals/ground_truth_test.jsonl")
    
    if not data_path.exists():
        print(f"⚠️ Warning: Data file not found at {data_path}")
        print("   Please provide a valid evaluation data file with 'question' field")
        exit(1)
    
    print(f"\n🔍 Starting evaluation of target application...")
    print(f"   Backend URL: {BACKEND_URL}")
    print(f"   Data file: {data_path}")
    print(f"   Evaluators: relevance, groundedness")
    
    # Run evaluation with the target function
    result = evaluate(
        data=str(data_path),
        target=evaluate_rag_application,
        evaluation_name="evaluate_rag_target_application",
        evaluators={
            "relevance": relevance_eval,
            "groundedness": groundedness_eval,
        },
        evaluator_config={
            "relevance": {
                "column_mapping": {
                    "query": "${data.question}",
                    "response": "${target.response}"
                }
            },
            "groundedness": {
                "column_mapping": {
                    "query": "${data.question}",
                    "response": "${target.response}",
                    "context": "${target.context}"
                }
            }
        },
        azure_ai_project=azure_ai_project,
        output_path="./evals/results_target.jsonl"
    )
    
    # Display results
    tabular_result = pd.DataFrame(result.get("rows"))
    
    print("\n" + "="*50)
    print("-----Summarized Metrics-----")
    pprint(result["metrics"])
    print("\n-----Tabular Result-----")
    pprint(tabular_result)
    print("\n-----Evaluation Complete-----")
    print(f"Results saved to: ./evals/results_target.jsonl")
    
    if "studio_url" in result:
        print(f"\n🔗 View evaluation results in Microsoft Foundry:")
        print(f"   {result['studio_url']}")
    
    print("="*50)


# ----------------------------------------------
# How to Run This Evaluation:
# 
# 1. Make sure backend application is running and copy the URI from Azure
#    - Login to Azure portal
#    - Find Azure Container App in resource group
#    - Copy Application Url and confirm the same value as BACKEND_URI in env file
#
# 2. Ensure you have evaluation data file:
#    - Default: evals/generate_truth_test.jsonl
#    - Format: Each line should have a "question" field
#    - Example: {"question": "What are the health benefits?"}
#    - Test file contains two records to shorten evaluation time.  Actual file is ground_truth.jsonl
#
# 3. Set required environment variables (loaded via load_azd_env):
#    - AZURE_AI_PROJECT_ENDPOINT (for new Foundry projects without workspace)
#    - BACKEND_URI (e.g. http://localhost:50505 or your deployed app URL)
#
# 4. Run the evaluation:
#    python evals/evaluate.py
#
# ----------------------------------------------
# Expected Output:
#
# The evaluation will:
# - Call your RAG application for each question in the data file
# - Evaluate relevance of responses to questions
# - Evaluate groundedness of responses based on retrieved context
# - Save results locally to evals/results_target.jsonl
# - Upload results to Azure AI Foundry portal
# - Display summarized metrics and tabular results
# ----------------------------------------------
