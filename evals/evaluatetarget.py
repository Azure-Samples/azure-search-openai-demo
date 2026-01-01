# ----------------------------------------------
# Evaluate Target Application (Azure Evaluation SDK)
# Evaluates the actual RAG application backend API
# Following the pattern from evaluate.py sample
# Uses Azure AI Foundry project for results upload
# ----------------------------------------------

# ----------------------------------------------
# 1. Create AI Project Client and Load Config
# ----------------------------------------------
import os
import json
import pandas as pd
import requests
from pathlib import Path
from typing import TypedDict
from azure.ai.projects import AIProjectClient
from azure.ai.evaluation import evaluate
from azure.ai.evaluation import RelevanceEvaluator, GroundednessEvaluator
from azure.ai.evaluation import AzureOpenAIModelConfiguration
from azure.identity import DefaultAzureCredential
from pprint import pprint

# Note: Environment variables are loaded in the if __name__ == "__main__" block
# to avoid issues with multiprocessing when spawning child processes

# ----------------------------------------------
# 2. Define Evaluator Model Configuration
# ----------------------------------------------
# These will be initialized in the main block after loading environment variables

# ----------------------------------------------
# 3. Define Target Function to Query RAG App
# ----------------------------------------------
# Set the backend URL - adjust based on where your app is running
BACKEND_URL = os.environ.get("BACKEND_URL", "https://capps-backend-poprbcmujix6c.blackdesert-c529f77d.francecentral.azurecontainerapps.io")


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
    try:
        # Call the /ask endpoint of the RAG application
        response = requests.post(
            f"{BACKEND_URL}/ask",
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
# 4. Run the Evaluation
#    View Results Locally (Saved as JSON)
#    Upload Results to AI Foundry Portal
# ----------------------------------------------
# Evaluation must be called inside of __main__, not on import
if __name__ == "__main__":
    import contextlib
    import multiprocessing
    from dotenv_azd import load_azd_env
    
    # Load environment variables FIRST, before any multiprocessing
    load_azd_env()
    
    # Configure Azure AI project for uploading results to AI Foundry
    azure_ai_project = {
        "subscription_id": os.environ.get("AZURE_SUBSCRIPTION_ID"),
        "resource_group_name": os.environ.get("AZURE_RESOURCE_GROUP"),
        "project_name": os.environ.get("AZURE_AI_PROJECT"),
    }
    
    # Define evaluator model configuration
    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.environ.get("AZURE_OPENAI_EVAL_DEPLOYMENT"),
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
        print(f"   Make sure the backend is running. Error: {e}")
        print(f"   You can start it with: 'python app/backend/app.py' or use the Development task")
        exit(1)
    
    # Define the path to evaluation data
    # You can use your existing data file or create a new one
    data_path = Path("evals/ground_truth.jsonl")
    
    if not data_path.exists():
        print(f"⚠️ Warning: Data file not found at {data_path}")
        print("   Please provide a valid evaluation data file with 'question' field")
        print("   Example format: {'question': 'What are the health benefits?'}")
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
        print(f"\n🔗 View evaluation results in AI Studio:")
        print(f"   {result['studio_url']}")
    
    print("="*50)


# ----------------------------------------------
# How to Run This Evaluation:
# 
# 1. Make sure the backend application is running:
#    - Run: python app/backend/app.py
#    - Or use VS Code task: "Backend: quart run"
#    - Or start full app: "Development" task
#
# 2. Ensure you have evaluation data file:
#    - Default: evals/results/baseline-ask/eval_results.jsonl
#    - Format: Each line should have a "question" field
#    - Example: {"question": "What are the health benefits?"}
#
# 3. Set required environment variables (loaded via load_azd_env):
#    - AZURE_SUBSCRIPTION_ID
#    - AZURE_RESOURCE_GROUP
#    - AZURE_AI_PROJECT
#    - AZURE_OPENAI_ENDPOINT
#    - AZURE_OPENAI_EVAL_DEPLOYMENT
#
# 4. Run the evaluation:
#    python evals/evaluatetarget.py
#
# Optional: Set custom backend URL
#    export BACKEND_URL=http://localhost:50505
#    python evals/evaluatetarget.py
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
#
# ----------------------------------------------
