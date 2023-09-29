import asyncio
import csv
import json
import logging
import os
import sys
from pathlib import Path

import urllib3
from azure.ai.generative.evaluate import evaluate
from azure.identity import DefaultAzureCredential

sys.path.append("app/backend")
import app  # noqa

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
                    "temperature": 0.0,
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


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f.readlines()]


def run_evaluation(testdata_filename):
    path = Path(__file__).parent.absolute() / testdata_filename
    data = load_jsonl(path)

    gpt_model = "gpt-4"
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
                "api_key": azure_credential.get_token("https://cognitiveservices.azure.com/.default").token,
                "deployment_id": "chat",
                "model": gpt_model,
            },
            "questions": "question",
            "contexts": "context",
        },
        # TODO: Try params?
    )

    columns = ["question", "gpt_similarity", "gpt_relevance", "gpt_fluency", "gpt_coherence", "gpt_groundedness"]
    gpt_ratings = results["artifacts"]
    rows = []

    metrics = {key: {"sum_scores": 0, "avg_score": 0, "pass_count": 0, "pass_rate": 0} for key in gpt_ratings.keys()}

    def passes_threshold(rating):
        return int(rating) >= 4

    for ind, input in enumerate(data):
        for key in gpt_ratings.keys():
            metrics[key]["sum_scores"] += int(gpt_ratings[key][ind])
            metrics[key]["avg_score"] = metrics[key]["sum_scores"] / (ind + 1)
            if passes_threshold(gpt_ratings[key][ind]):
                metrics[key]["pass_count"] += 1
            metrics[key]["pass_rate"] = metrics[key]["pass_count"] / (ind + 1)
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
    # now sort rows by question for easier diffing if questions get added later
    rows.sort(key=lambda x: x[0])

    with open("evaluation/per_question.csv", "w") as question_file:
        writer = csv.writer(question_file, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)

    # summary statistics
    with open("evaluation/summary.csv", "w") as summary_file:
        writer = csv.writer(summary_file, lineterminator="\n")
        columns = ["gpt_metric", "avg_score", "pass_count", "pass_rate"]
        writer.writerow(columns)
        for key in metrics.keys():
            writer.writerow([key, metrics[key]["avg_score"], metrics[key]["pass_count"], metrics[key]["pass_rate"]])

    with open("evaluation/run_env.csv", "w") as metadata_file:
        writer = csv.writer(metadata_file, lineterminator="\n")
        columns = ["property", "value"]
        writer.writerow(columns)
        writer.writerow(["Evaluation GPT model", gpt_model])
        writer.writerow(["App GPT model", os.environ["AZURE_OPENAI_CHATGPT_MODEL"]])


if __name__ == "__main__":
    run_evaluation("qa.jsonl")
