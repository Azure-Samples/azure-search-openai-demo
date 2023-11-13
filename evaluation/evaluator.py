import asyncio
import json
import logging
import os
import re
from pathlib import Path

import urllib3
from azure.ai.generative.evaluate import evaluate
from azure.identity import AzureDeveloperCliCredential

logging.basicConfig(level=logging.DEBUG)

EVAL_DIR = Path(__file__).parent.absolute()
# TODO: multi-turn conversation history in the future


def deployed_target(question, overrides={}):
    http = urllib3.PoolManager()
    url = "https://app-backend-j25rgqsibtmlo.azurewebsites.net/chat"
    headers = {"Content-Type": "application/json"}
    body = {
        "messages": [{"content": question, "role": "user"}],
        "stream": False,
        "context": {"overrides": overrides},
    }
    r = http.request("POST", url, headers=headers, body=json.dumps(body))
    # todo: add context without filenames? needed?
    try:
        response_dict = json.loads(r.data.decode("utf-8"))
        return {
            "question": question,
            "answer": response_dict["choices"][0]["message"]["content"],
            "context": "\n\n".join(response_dict["choices"][0]["context"]["data_points"]),
        }
    except Exception as e:
        logging.error(e)
        print(r.data.decode("utf-8"))
        return {
            "question": question,
            "answer": "ERROR",
            "context": "ERROR",
        }


async def send_chat_request(question) -> dict:
    import sys

    sys.path.append("app/backend")
    import app  # noqa

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


def local_target(question):
    response_dict = asyncio.run(send_chat_request(question))
    return {
        "question": question,
        "answer": response_dict["answer"],
        "context": "\n\n".join(response_dict["data_points"]),
    }


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f.readlines()]


def run_evaluation(testdata_filename, destination_dir, overrides={}):
    path = EVAL_DIR / testdata_filename
    data = load_jsonl(path)

    gpt_model = os.environ["AZURE_OPENAI_EVALGPT_MODEL"]
    azure_credential = AzureDeveloperCliCredential()
    aoai_config = {
        "api_type": "azure_ad",
        "api_base": f"https://{os.environ['AZURE_OPENAI_SERVICE']}.openai.azure.com",
        "api_key": azure_credential.get_token("https://cognitiveservices.azure.com/.default").token,
        "api_version": "2023-07-01-preview",
        "deployment_id": os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"],
    }

    gpt_metrics = ["gpt_groundedness", "gpt_relevance", "gpt_coherence", "gpt_similarity"]
    results = evaluate(
        evaluation_name="baseline-evaluation",
        target=lambda question: deployed_target(question, overrides),
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
        output_path=destination_dir,
    )

    eval_results_filename = list(results.artifacts.keys())[0]
    with open(Path(destination_dir) / eval_results_filename) as f:
        questions_with_ratings = [json.loads(question_json) for question_json in f.readlines()]

    metrics = {
        metric_name: {
            "mean_rating": round(results.metrics_summary[f"mean_{metric_name}"], 2),
            "pass_count": 0,
            "pass_rate": 0,
        }
        for metric_name in gpt_metrics
    }
    total_length = 0
    max_length = 0
    min_length = 9999999999
    total_with_citation = 0

    def passes_threshold(rating):
        return int(rating) >= 4

    for ind, question_with_rating in enumerate(questions_with_ratings):
        total_length += len(question_with_rating["answer"])
        max_length = max(max_length, len(question_with_rating["answer"]))
        min_length = min(min_length, len(question_with_rating["answer"]))
        total_with_citation += 1 if re.search(r"\[[^\]]+\]", question_with_rating["answer"]) else 0
        for metric_name in gpt_metrics:
            if passes_threshold(question_with_rating[metric_name]):
                metrics[metric_name]["pass_count"] += 1
            metrics[metric_name]["pass_rate"] = round(metrics[metric_name]["pass_count"] / (ind + 1), 2)
    metrics["answer_length"] = {
        "total": total_length,
        "mean": round(total_length / len(questions_with_ratings), 2),
        "max": max_length,
        "min": min_length,
    }
    metrics["answer_has_citation"] = {
        "total": total_with_citation,
        "rate": round(total_with_citation / len(questions_with_ratings), 2),
    }

    # summary statistics
    with open(Path(destination_dir) / "summary.json", "w") as summary_file:
        summary_file.write(json.dumps(metrics, indent=4))

    with open(Path(destination_dir) / "parameters.json", "w") as parameters_file:
        parameters = {
            "overrides": overrides,
            "evaluation_gpt_model": gpt_model,
            # "app_gpt_model" # cant do that with deployed
        }
        parameters_file.write(json.dumps(parameters, indent=4))


if __name__ == "__main__":
    run_evaluation(
        "input/qa.jsonl",
        destination_dir=EVAL_DIR / "results/no_semantic_ranker_prompt_chris3",
        overrides={
            "retrieval_mode": "hybrid",
            "semantic_ranker": False,
            "semantic_captions": False,
            "top": 3,
            "suggest_followup_questions": False,
            "prompt_template": open(EVAL_DIR / "input/prompt_chris.txt").read(),
        },
    )
