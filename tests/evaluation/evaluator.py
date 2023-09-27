import asyncio
import json
import logging
import os

import urllib3
from azure.ai.generative.evaluate import evaluate
from azure.identity import DefaultAzureCredential

import app

logging.basicConfig(level=logging.DEBUG)
# loadenv from a .azure/env file

# connects to project defined in the config.json file at the root of the repo
# use "ai init" to update this to point at your project
azure_credential = DefaultAzureCredential()

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


async def send_chat_request(question) -> dict:
    quart_app = app.create_app()
    async with quart_app.test_app() as test_app:
        test_client = test_app.test_client()
        response = await test_client.post(
            "/chat",
            json={
                "history": [{"user": question}],
                "approach": "rrr",
                "overrides": {
                    "retrieval_mode": "hybrid",
                    "semantic_ranker": True,
                    "semantic_captions": False,
                    "top": 3,
                    "suggest_followup_questions": False,
                },
            },
        )
        response_dict = await response.get_json()
        return response_dict


def local_qna(question):
    response_dict = asyncio.run(send_chat_request(question))
    return {
        "question": question,
        "answer": response_dict["answer"],
        "context": "\n\n".join(response_dict["data_points"]),
    }


# Loading data
def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f.readlines()]


def test_evaluation(snapshot):
    # get path of this file
    this_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(this_path + "/data.jsonl")
    data = load_jsonl(path)

    # Evaluate the default vs the improved system prompt to see if the improved prompt
    # performs consistently better across a larger set of inputs
    openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")

    results = evaluate(
        evaluation_name="baseline-evaluation",
        asset=local_qna,
        data=data,
        task_type="qa",
        prediction_data="answer",
        truth_data="truth",
        metrics_config={
            "openai_params": {
                "api_version": "2023-05-15",
                "api_base": "https://cog-pg6yesvgqiudc.openai.azure.com/",
                "api_type": "azure_ad",
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
    # save a snapshot of the evaluation
    # evaluation_model_name = "gpt-4"
    # generation_model_name = os.environ["AZURE_OPENAI_CHATGPT_MODEL"]
    # filename = f"{evaluation_model_name}_vs_{generation_model_name}.csv"
    columns = ["question", "gpt_similarity", "gpt_relevance", "gpt_fluency", "gpt_coherence", "gpt_groundedness"]
    gpt_ratings = results["artifacts"]
    rows = []
    # threshold = 4
    for ind, input in enumerate(data):
        # if < threshold, PASS, else FAIL
        rows.append(
            [
                input["question"],
                gpt_ratings["gpt_similarity"][ind],
                gpt_ratings["gpt_relevance"][ind],
                gpt_ratings["gpt_fluency"][ind],
                gpt_ratings["gpt_coherence"][ind],
                gpt_ratings["gpt_groundedness"][ind],
            ]
        )
    # now sort rows by question
    rows.sort(key=lambda x: x[0])

    # save rows to a string using csv writer
    import csv
    import io

    f = io.StringIO()
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    # get string
    f.seek(0)
    # save to snapshot
    print(f.getvalue())
    print(results["metrics"])
