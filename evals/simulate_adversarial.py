import asyncio
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional

import requests
from azure.ai.evaluation.simulator import AdversarialScenario, AdversarialSimulator
from azure.identity import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from rich.logging import RichHandler

logger = logging.getLogger("ragapp")

root_dir = pathlib.Path(__file__).parent


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


async def run_simulator():
    azure_ai_project = {
        "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID"),
        "resource_group_name": os.getenv("AZURE_RESOURCE_GROUP"),
        "project_name": os.getenv("AZURE_AI_PROJECT"),
    }

    scenario = AdversarialScenario.ADVERSARIAL_QA
    adversarial_simulator = AdversarialSimulator(azure_ai_project=azure_ai_project, credential=get_azure_credential())

    outputs = await adversarial_simulator(
        scenario=scenario,  # required adversarial scenario to simulate
        target=callback,  # callback function to simulate against
        max_conversation_turns=1,  # optional, applicable only to conversation scenario
        max_simulation_results=3,  # optional
    )

    # By default simulator outputs json, use the following helper function to convert to QA pairs in jsonl format
    print(outputs.to_eval_qr_json_lines())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger.setLevel(logging.INFO)
    load_azd_env()

    asyncio.run(run_simulator())
