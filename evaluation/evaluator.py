import json
import logging
import os
from pprint import pprint

import urllib3
from azure.ai.generative.evaluate import evaluate
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.DEBUG)
# loadenv from a .azure/env file

# connects to project defined in the config.json file at the root of the repo
# use "ai init" to update this to point at your project
azure_credential = DefaultAzureCredential()
# client = AIClient.from_config(azure_credential) # Azure ML Studio, https://learn.microsoft.com/en-us/azure/templates/microsoft.machinelearningservices/workspaces?pivots=deployment-language-bicep

# multi-turn conversation history in the future


def qna(question):
    http = urllib3.PoolManager()
    url = "https://app-backend-pg6yesvgqiudc.azurewebsites.net/chat"
    headers = {"Content-Type": "application/json"}
    body = {
        "history": [{"user": question}],
        "approach": "rrr",
        "overrides": {
            "retrieval_mode": "hybrid",
            "semantic_ranker": True,
            "semantic_captions": False,
            "top": 3,
            "suggest_followup_questions": False,
        },
    }
    r = http.request("POST", url, headers=headers, body=json.dumps(body))
    # todo: add context without filenames
    return {
        "question": question,
        "answer": json.loads(r.data.decode("utf-8"))["answer"],
        "context": "\n\n".join(json.loads(r.data.decode("utf-8"))["data_points"]),
    }


# Loading data
def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f.readlines()]


path = os.path.join(os.getcwd() + "/evaluation/data.jsonl")
data = load_jsonl(path)

# Evaluate the default vs the improved system prompt to see if the improved prompt
# performs consistently better across a larger set of inputs
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")

result = evaluate(
    evaluation_name="baseline-evaluation",
    asset=qna,
    data=data,
    task_type="qa",
    prediction_data="answer",
    truth_data="truth",
    metrics_config={
        "openai_params": {
            "api_version": "2023-05-15",
            "api_base": "https://cog-pg6yesvgqiudc.openai.azure.com/",
            "api_type": "azure_ad",  # TODO: try azure_ad instead
            "api_key": openai_token.token,
            "deployment_id": "chat",
            "model": "gpt-4",
        },
        "questions": "question",
        "contexts": "context",
    },
    # TODO: Try params
    # tracking_uri=client.tracking_uri,
)
pprint(result)

# Print a link to open the evalautions page in AI Studio
# print(f"Open in AI Studio: https://ml.azure.com/projectEvaluation?flight=AiStudio,DeployChatWebapp,SkipAADRegistration/projectEvaluation&wsid=/subscriptions/{client.subscription_id}/resourceGroups/{client.resource_group_name}/providers/Microsoft.MachineLearningServices/workspaces/{client.project_name}")
