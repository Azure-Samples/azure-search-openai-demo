import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from azure.ai.evaluation.simulator import Simulator
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryType,
)
from dotenv_azd import load_azd_env

logger = logging.getLogger("evals")

CURRENT_DIR = Path(__file__).parent


async def callback(
    messages: List[Dict],
    stream: bool = False,
    session_state: Any = None,
    context: Optional[Dict[str, Any]] = None,
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
                "use_oid_security_filter": False,
                "use_groups_security_filter": False,
                "vector_fields": ["embedding"],
                "use_gpt4v": False,
                "gpt4v_input": "textAndImages",
                "seed": 1,
            }
        },
    }
    url = "http://localhost:50505/chat"
    r = requests.post(url, headers=headers, json=body)
    response = r.json()
    response["messages"] = messages_list + [response["message"]]
    return response


def get_simulator() -> Simulator:
    azure_endpoint = f"https://{os.getenv('AZURE_OPENAI_SERVICE')}.openai.azure.com"
    # JSON mode supported model preferred to avoid errors ex. gpt-4o-mini, gpt-4o, gpt-4 (1106)
    azure_deployment = os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT")
    model_config = {
        "azure_endpoint": azure_endpoint,
        "azure_deployment": azure_deployment,
    }
    # Simulator will use DefaultAzureCredential, so make sure your Azure CLI is logged in to correct tenant
    simulator = Simulator(model_config=model_config)
    return simulator


def get_azure_credential():
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    if AZURE_TENANT_ID:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential with tenant_id %s", AZURE_TENANT_ID)
        azure_credential = AzureDeveloperCliCredential(tenant_id=AZURE_TENANT_ID, process_timeout=60)
    else:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential for home tenant")
        azure_credential = AzureDeveloperCliCredential(process_timeout=60)
    return azure_credential


def generate_text_from_index(azure_credential, search_term: str) -> str:
    search_client = SearchClient(
        endpoint=f"https://{os.getenv('AZURE_SEARCH_SERVICE')}.search.windows.net",
        index_name=os.getenv("AZURE_SEARCH_INDEX"),
        credential=azure_credential,
    )
    query_language = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")
    query_speller = os.getenv("AZURE_SEARCH_QUERY_SPELLER", "lexicon")
    search_results = search_client.search(
        search_text=search_term,
        top=10,
        query_type=QueryType.SEMANTIC,
        query_language=query_language,
        query_speller=query_speller,
        semantic_configuration_name="default",
        semantic_query=search_term,
    )
    text = ""
    for result in search_results:
        text += result["content"]
    return text[0:5000]


async def generate_ground_truth(azure_credential, simulations: list[dict], num_per_task: int = 2):
    """
    Generates single-turn ground truth Q/A pairs for given search term/tasks combos.
    """
    simulator = get_simulator()
    for simulation in simulations:
        text = generate_text_from_index(azure_credential, simulation["search_term"])
        tasks = simulation["tasks"]
        outputs = await simulator(
            target=callback,
            text=text,
            max_conversation_turns=1,
            num_queries=len(tasks) * num_per_task,
            tasks=tasks * num_per_task,
        )
        qa_pairs = []
        for output in outputs:
            qa_pairs.append({"question": output["messages"][0]["content"], "truth": output["messages"][1]["content"]})
        with open(CURRENT_DIR / "ground_truth.jsonl", "a") as f:
            for qa_pair in qa_pairs:
                f.write(json.dumps(qa_pair) + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    logger.setLevel(logging.INFO)
    load_azd_env()

    azure_credential = get_azure_credential()

    with open(CURRENT_DIR / "generate_config.json") as f:
        generate_config = json.load(f)
        simulations = generate_config["simulations"]
        num_per_task = generate_config.get("num_per_task", 2)

    asyncio.run(generate_ground_truth(azure_credential, simulations, num_per_task))
