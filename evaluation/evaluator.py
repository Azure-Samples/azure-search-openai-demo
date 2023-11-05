import asyncio
import csv
import json
import logging
import sys
from pathlib import Path

import urllib3
from azure.ai.generative.evaluate import evaluate
from azure.ai.resources.entities import AzureOpenAIModelConfiguration
from azure.identity import AzureDeveloperCliCredential

sys.path.append("app/backend")
import app  # noqa

logging.basicConfig(level=logging.DEBUG)
# loadenv from a .azure/env file

# connects to project defined in the config.json file at the root of the repo
# use "ai init" to update this to point at your project
azure_credential = AzureDeveloperCliCredential()

# multi-turn conversation history in the future


def qna(question):
    http = urllib3.PoolManager()
    url = "https://app-backend-j25rgqsibtmlo.azurewebsites.net/chat"
    headers = {"Content-Type": "application/json"}
    body = {
        "messages": [{"content": question, "role": "user"}],
        "stream": False,
        "context": {
            "overrides": {
                "retrieval_mode": "hybrid",
                "semantic_ranker": True,
                "semantic_captions": False,
                "top": 3,
                "suggest_followup_questions": False,
            }
        },
    }
    r = http.request("POST", url, headers=headers, body=json.dumps(body))
    # todo: add context without filenames
    response_dict = json.loads(r.data.decode("utf-8"))
    return {
        "question": question,
        "answer": response_dict["choices"][0]["message"]["content"],
        "context": "\n\n".join(response_dict["choices"][0]["context"]["data_points"]),
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
    data = load_jsonl(path)[0:5]

    gpt_model = "gpt-4"

    aoai_config = AzureOpenAIModelConfiguration(
        api_base="https://cog-pg6yesvgqiudc.openai.azure.com/",
        api_key=azure_credential.get_token("https://cognitiveservices.azure.com/.default").token,
        api_version="2023-05-15",
        deployment_name="chat",
        model_name=gpt_model,
        model_kwargs={},
    )
    aoai_config = {
        "api_type": "azure_ad",
        "api_base": "https://cog-pg6yesvgqiudc.openai.azure.com/",
        "api_key": azure_credential.get_token("https://cognitiveservices.azure.com/.default").token,
        "api_version": "2023-07-01-preview",
        "deployment_id": "chat",
    }
    logging.basicConfig(level=logging.DEBUG)
    gpt_metrics = ["gpt_groundedness", "gpt_relevance", "gpt_coherence", "gpt_fluency", "gpt_similarity"]
    results = evaluate(
        evaluation_name="baseline-evaluation",
        target=qna,
        data=data,
        task_type="qa",
        metrics_list=gpt_metrics,
        model_config=aoai_config,
        data_mapping={
            # Matches qa.jsonl
            "questions": "question",  # column of data providing input to model
            "y_test": "truth",  # column of data providing ground truth answer, optional for default metrics
            # Matches return value of qna()
            "contexts": "context",  # column of data providing context for each input
            "y_pred": "answer",  # column of data providing output from model
        },
        tracking=False,
        output_path="evaluation",
    )
    print(results)
    questions_with_ratings = open("evaluation/eval_results.jsonl").readlines()

    metrics = {
        metric_name: {"sum_scores": 0, "avg_score": 0, "pass_count": 0, "pass_rate": 0} for metric_name in gpt_metrics
    }

    def passes_threshold(rating):
        return int(rating) >= 4

    rows = []
    for ind, question_json in enumerate(questions_with_ratings):
        question_with_rating = json.loads(question_json)
        for metric_name in gpt_metrics:
            metrics[metric_name]["sum_scores"] += int(question_with_rating[metric_name])
            metrics[metric_name]["avg_score"] = metrics[metric_name]["sum_scores"] / (ind + 1)
            if passes_threshold(question_with_rating[metric_name]):
                metrics[metric_name]["pass_count"] += 1
            metrics[metric_name]["pass_rate"] = metrics[metric_name]["pass_count"] / (ind + 1)
        rows.append(list(question_with_rating.values()))

    # now sort rows by question for easier diffing if questions get added later
    rows.sort(key=lambda x: x[0])

    columns = ["question"] + gpt_metrics
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
        # writer.writerow(["App GPT model", os.environ["AZURE_OPENAI_CHATGPT_MODEL"]]) # cant do that with deployed


if __name__ == "__main__":
    run_evaluation("qa.jsonl")
