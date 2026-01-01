#Evalute from Getting started documents on Microsoft Learn 
# Run Evaluation Locally (Azure Evaluation SDK)
# Azure OpenAI Service deployed in Azure AI Foundry manually
# Azure Foundry and Project without a Hub
# Save File and upload results to AI Foundry Evaluation Dashboard
# Same data and no groundtruth.jsonl files
# Run this against Model and no targert URL
# Connect with AI Project in Foundry
# Single Turn
from azure.ai.evaluation import evaluate
from azure.ai.evaluation import RelevanceEvaluator
from azure.ai.evaluation import GroundednessEvaluator, AzureOpenAIModelConfiguration
from dotenv_azd import load_azd_env
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

import json
import os

# Load environment variables
load_azd_env()

# Configure Azure AI project for uploading results to AI Foundry

azure_ai_project = {
    "subscription_id": os.environ.get("AZURE_SUBSCRIPTION_ID"),
    "resource_group_name": os.environ.get("AZURE_RESOURCE_GROUP"),
    "project_name": os.environ.get("AZURE_AI_PROJECT"),
}

#azure_ai_project = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")

model_config = AzureOpenAIModelConfiguration(
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.environ.get("AZURE_OPENAI_EVAL_DEPLOYMENT"),
    api_version="2024-08-01-preview",
)

# Initialize the Relevance evaluator:
relevance_eval = RelevanceEvaluator(model_config)

#query = "What is the capital of life?"
#response = "Paris."

# Call the evaluator to get results
result = evaluate(
    data="evals/results/baseline-ask/eval_results.jsonl",
    evaluators={"relevance": relevance_eval},
    evaluator_config={
        "relevance": {
            "column_mapping": {
                "query": "${data.question}",
                "response": "${data.answer}"
            }
        }
    },
    azure_ai_project=azure_ai_project,
    output_path="./evals/results_jdv.jsonl"
)

print(json.dumps(result, indent=4))
