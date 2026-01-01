import argparse
import asyncio
import json
import logging
import os
import pathlib
from enum import Enum
from typing import Any, Optional

import pandas as pd
import requests
from azure.ai.evaluation import ContentSafetyEvaluator, evaluate
from azure.ai.evaluation.simulator import (
    AdversarialScenario,
    AdversarialSimulator,
    SupportedLanguages,
)
from azure.identity import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from pprint import pprint
from rich.logging import RichHandler
from rich.progress import track

logger = logging.getLogger("ragapp")

root_dir = pathlib.Path(__file__).parent


class HarmSeverityLevel(Enum):
    """Harm severity levels reported by the Azure AI Evaluator service.
    These constants have been copied from the azure-ai-evaluation package,
    where they're currently in a private module.
    """

    VeryLow = "Very low"
    Low = "Low"
    Medium = "Medium"
    High = "High"


def get_azure_credential():
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    if AZURE_TENANT_ID:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential with tenant_id %s", AZURE_TENANT_ID)
        azure_credential = AzureDeveloperCliCredential(tenant_id=AZURE_TENANT_ID, process_timeout=60)
    else:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential for home tenant")
        azure_credential = AzureDeveloperCliCredential(process_timeout=60)
    return azure_credential


async def callback(
    messages: list[dict],
    stream: bool = False,
    session_state: Any = None,
    context: Optional[dict[str, Any]] = None,
    target_url: str = "http://localhost:50505/chat",
):
    messages_list = messages["messages"]
    latest_message = messages_list[-1]
    query = latest_message["content"]
    headers = {"Content-Type": "application/json"}
    body = {
        "messages": [{"content": query, "role": "user"}],
        "stream": stream,
        "context": {
            "overrides": {
                "top": 3,
                "temperature": 0.3,
                "minimum_reranker_score": 0,
                "minimum_search_score": 0,
                "retrieval_mode": "hybrid",
                "semantic_ranker": True,
                "semantic_captions": False,
                "suggest_followup_questions": False,
                "vector_fields": ["embedding"],
                "use_gpt4v": False,
                "gpt4v_input": "textAndImages",
                "seed": 1,
            }
        },
    }
    url = target_url
    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        response = r.json()
        
        if "error" in response:
            message = {"content": response["error"], "role": "assistant"}
        else:
            message = response.get("message", {"content": "No response", "role": "assistant"})
        
        response["messages"] = messages_list + [message]
        return response
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error {r.status_code}: {e}")
        logger.error(f"Request URL: {url}")
        logger.error(f"Response text: {r.text[:500]}")
        if r.status_code == 400:
            logger.error(f"Request body was: {json.dumps(body, indent=2)}")
        return {
            "messages": messages_list + [{"content": f"Error: HTTP {r.status_code} - {r.text[:100]}", "role": "assistant"}]
        }
    except requests.exceptions.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response status: {r.status_code}, Response text: {r.text[:200]}")
        return {
            "messages": messages_list + [{"content": f"Error: Invalid JSON response from backend", "role": "assistant"}]
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {
            "messages": messages_list + [{"content": f"Error: Request failed - {str(e)}", "role": "assistant"}]
        }


async def run_simulator(target_url: str, max_simulations: int):
    """Run adversarial simulator and save outputs to JSONL for evaluation."""
    credential = get_azure_credential()
    azure_ai_project = {
        "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID"),
        "resource_group_name": os.getenv("AZURE_RESOURCE_GROUP"),
        "project_name": os.getenv("AZURE_AI_PROJECT"),
    }

    # Simulate single-turn question-and-answering against the app
    scenario = AdversarialScenario.ADVERSARIAL_QA
    adversarial_simulator = AdversarialSimulator(azure_ai_project=azure_ai_project, credential=credential)

    logger.info(f"Running adversarial simulation with {max_simulations} max simulations...")
    outputs = await adversarial_simulator(
        scenario=scenario,
        target=lambda messages, stream=False, session_state=None, context=None: callback(
            messages, stream, session_state, context, target_url
        ),
        max_simulation_results=max_simulations,
        language=SupportedLanguages.English,  # Match this to your app language
        randomization_seed=1,  # For more consistent results, use a fixed seed
    )

    # Save simulation outputs as JSONL for evaluation
    # Note: We save query and response separately for safety evaluation
    simulation_data_path = root_dir / "redteam_results" / "simulation_data.jsonl"
    simulation_data_path.parent.mkdir(exist_ok=True)
    
    logger.info(f"Saving {len(outputs)} simulation outputs to {simulation_data_path}")
    valid_outputs = 0
    with open(simulation_data_path, "w") as f:
        for output in outputs:
            # Skip outputs that don't have both query and response
            if "messages" not in output or len(output["messages"]) < 2:
                logger.warning(f"Skipping incomplete simulation output: {output}")
                continue
            
            query = output["messages"][0]["content"]
            response = output["messages"][1]["content"]
            
            # Skip if response is empty or None
            if not response:
                logger.warning(f"Skipping simulation with empty response for query: {query}")
                continue
                
            f.write(json.dumps({"query": query, "response": response}) + "\n")
            valid_outputs += 1
    
    logger.info(f"Saved {valid_outputs} valid outputs out of {len(outputs)} total simulations")
    return azure_ai_project, str(simulation_data_path), valid_outputs


def run_safety_evaluation(azure_ai_project: dict, data_path: str, num_simulations: int):
    """Run safety evaluation using evaluate() function to upload results to Azure Portal."""
    
    # Check if we have valid data to evaluate
    if num_simulations == 0:
        logger.error("No valid simulation outputs to evaluate. All simulations failed to generate responses.")
        logger.error("This usually happens when:")
        logger.error("  1. The target URL is not accessible")
        logger.error("  2. The backend is not responding correctly")
        logger.error("  3. The backend is rejecting the adversarial queries")
        logger.error("\nCheck the warnings above for more details about why simulations failed.")
        return
    
    credential = get_azure_credential()
    
    # Initialize ContentSafetyEvaluator
    safety_evaluator = ContentSafetyEvaluator(
        credential=credential,
        azure_ai_project=azure_ai_project
    )
    
    logger.info(f"\n🔍 Starting safety evaluation...")
    logger.info(f"   Data file: {data_path}")
    logger.info(f"   Number of simulations: {num_simulations}")
    logger.info(f"   Evaluator: ContentSafetyEvaluator (hate_unfairness, sexual, violence, self_harm)")
    
    # Run evaluation with ContentSafetyEvaluator
    # The target is identity function since we already have query and response in data
    result = evaluate(
        data=data_path,
        evaluators={"safety": safety_evaluator},
        evaluator_config={
            "safety": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}"
                }
            }
        },
        azure_ai_project=azure_ai_project,
        evaluation_name="safety_evaluation_adversarial",
        output_path=str(root_dir / "safety_results.jsonl")
    )
    
    # Display results
    tabular_result = pd.DataFrame(result.get("rows"))
    
    print("\n" + "="*50)
    print("-----Summarized Metrics-----")
    pprint(result["metrics"])
    print("\n-----Tabular Result Preview (first 5 rows)-----")
    print(tabular_result.head())
    print("\n-----Evaluation Complete-----")
    print(f"Results saved to: {root_dir / 'safety_results.jsonl'}")
    
    if "studio_url" in result:
        print(f"\n🔗 View evaluation results in AI Studio:")
        print(f"   {result['studio_url']}")
    
    print("="*50)
    
    # Also save summary metrics to JSON for backwards compatibility
    with open(root_dir / "safety_results.json", "w") as f:
        json.dump(result["metrics"], f, indent=2)
    logger.info(f"Summary metrics also saved to: {root_dir / 'safety_results.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run safety evaluation simulator.")
    parser.add_argument(
        "--target_url", type=str, default="http://localhost:50505/chat", help="Target URL for the callback."
    )
    parser.add_argument(
        "--max_simulations", type=int, default=200, help="Maximum number of simulations (question/response pairs)."
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger.setLevel(logging.INFO)
    load_azd_env()

    # Step 1: Run adversarial simulation to generate test data
    azure_ai_project, data_path, num_simulations = asyncio.run(
        run_simulator(args.target_url, args.max_simulations)
    )
    
    # Step 2: Run safety evaluation using evaluate() function (uploads to Azure Portal)
    run_safety_evaluation(azure_ai_project, data_path, num_simulations)
