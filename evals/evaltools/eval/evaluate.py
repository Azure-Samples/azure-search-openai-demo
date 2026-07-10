import json
import logging
import os
import time
from pathlib import Path

import jmespath
import pandas as pd
import requests
from azure.ai.evaluation import AzureOpenAIModelConfiguration
from rich.progress import track

from .. import service_setup
from .evaluate_metrics import metrics_by_name

logger = logging.getLogger("evaltools")

# Timeout (in seconds) for requests to the target chat endpoint.
# Generous to allow for LLM generation latency, but bounded so runs fail fast if the target hangs.
TARGET_REQUEST_TIMEOUT = 120


def send_question_to_target(
    question: str,
    url: str,
    parameters: dict | None = None,
    raise_error=False,
    response_answer_jmespath="output_text",
    response_context_jmespath="context.data_points.text",
):
    parameters = parameters or {}
    headers = {"Content-Type": "application/json"}
    body = {
        "messages": [{"content": question, "role": "user"}],
        "context": parameters,
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=TARGET_REQUEST_TIMEOUT)
        r.encoding = "utf-8"
        # Surface HTTP errors (4xx/5xx) as HTTP errors with a status code, rather than
        # letting them fall through to the JSON/schema handling below and producing a
        # misleading "not valid JSON" diagnostic.
        r.raise_for_status()

        latency = r.elapsed.total_seconds()

        try:
            response_dict = r.json()
        except json.JSONDecodeError:
            raise ValueError(
                f"Response from target {url} is not valid JSON:\n\n{r.text} \n"
                "Make sure that your configuration points at a chat endpoint that returns a single JSON object.\n"
            )

        try:
            answer = jmespath.search(response_answer_jmespath, response_dict)
            if answer is None:
                raise ValueError("Answer is missing")
            data_points = jmespath.search(response_context_jmespath, response_dict)
            if isinstance(data_points, dict):
                context = json.dumps(data_points, ensure_ascii=False)
            elif isinstance(data_points, list):
                context = "\n\n".join(data_points)
            elif data_points is not None:
                # Hopefully it's a string
                context = data_points
            else:
                raise ValueError("Context is missing")
        except Exception:
            raise ValueError(
                "Response does not adhere to the expected schema. "
                f"The answer should be accessible via the JMESPath expression '{response_answer_jmespath}' "
                f"and the context should be accessible via the JMESPath expression '{response_context_jmespath}'. "
                "Either adjust the app response or adjust send_question_to_target() in evaluate.py "
                f"to match the actual schema.\nResponse: {response_dict}"
            )

        response_obj = {"answer": answer, "context": context, "latency": latency}
        return response_obj
    except Exception as e:
        if raise_error:
            raise
        return {
            "answer": str(e),
            "context": str(e),
            "latency": -1,
        }


def truncate_for_log(s: str, max_length=50):
    s = str(s)
    return s if len(s) < max_length else s[:max_length] + "..."


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]


def run_evaluation(
    openai_config: AzureOpenAIModelConfiguration,
    testdata_path: Path,
    results_dir: Path,
    target_url: str,
    target_parameters=None,
    requested_metrics=None,
    num_questions=None,
    target_response_answer_jmespath="output_text",
    target_response_context_jmespath="context.data_points.text",
    model=None,
    azure_credential=None,
):
    target_parameters = target_parameters or {}
    requested_metrics = requested_metrics or []
    logger.info("Running evaluation using data from %s", testdata_path)
    testdata = load_jsonl(testdata_path)
    if num_questions:
        logger.info("Limiting evaluation to %s questions", num_questions)
        testdata = testdata[:num_questions]

    logger.info("Sending a test question to the target to ensure it is running...")
    try:
        question = "What information is in your knowledge base?"
        target_data = send_question_to_target(
            question,
            target_url,
            target_parameters,
            raise_error=True,
            response_answer_jmespath=target_response_answer_jmespath,
            response_context_jmespath=target_response_context_jmespath,
        )
        logger.info(
            'Successfully received response from target for question: "%s"\n"answer": "%s"\n"context": "%s"',
            truncate_for_log(question),
            truncate_for_log(target_data["answer"]),
            truncate_for_log(target_data["context"]),
        )
    except Exception as e:
        logger.error("Failed to send a test question to the target due to error: \n%s", e)
        return False

    logger.info("Sending a test chat completion to the GPT deployment to ensure it is running...")
    model_or_deployment = openai_config.get("azure_deployment") or model
    gpt_response = service_setup.get_openai_client(openai_config, azure_credential).responses.create(
        model=model_or_deployment,
        input="Hello!",
    )
    logger.info('Successfully received response from GPT: "%s"', gpt_response.output_text)

    logger.info("Starting evaluation...")
    for metric in requested_metrics:
        if metric not in metrics_by_name:
            logger.error(f"Requested metric {metric} is not available. Available metrics: {metrics_by_name.keys()}")
            return False

    requested_metrics = [
        metrics_by_name[metric_name] for metric_name in requested_metrics if metric_name in metrics_by_name
    ]

    def evaluate_row(row):
        output = {}
        output["question"] = row["question"]
        output["truth"] = row["truth"]
        target_response = send_question_to_target(
            question=row["question"],
            url=target_url,
            parameters=target_parameters,
            response_answer_jmespath=target_response_answer_jmespath,
            response_context_jmespath=target_response_context_jmespath,
        )
        output.update(target_response)
        for metric in requested_metrics:
            result = metric.evaluator_fn(openai_config=openai_config, azure_credential=azure_credential)(
                query=row["question"],
                response=output["answer"],
                context=output["context"],
                ground_truth=row["truth"],
            )
            output.update(result)

        return output

    # Run evaluations in serial to avoid rate limiting
    questions_with_ratings = []
    for row in track(testdata, description="Processing..."):
        questions_with_ratings.append(evaluate_row(row))

    logger.info("Evaluation calls have completed. Calculating overall metrics now...")
    # Make the results directory if it doesn't exist
    results_dir.mkdir(parents=True, exist_ok=True)
    # Save the results
    with open(results_dir / "eval_results.jsonl", "w", encoding="utf-8") as results_file:
        for row in questions_with_ratings:
            results_file.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Calculate aggregate metrics
    df = pd.DataFrame(questions_with_ratings)
    summary = {}
    for metric in requested_metrics:
        summary[metric.METRIC_NAME] = metric.get_aggregate_stats(df)
    # add a metric for the number of questions
    summary["num_questions"] = {"total": len(df)}

    # summary statistics
    with open(results_dir / "summary.json", "w", encoding="utf-8") as summary_file:
        summary_file.write(json.dumps(summary, indent=4))

    with open(results_dir / "evaluate_parameters.json", "w", encoding="utf-8") as parameters_file:
        parameters = {
            "evaluation_gpt_model": model,
            "evaluation_timestamp": int(time.time()),
            "testdata_path": os.path.relpath(testdata_path, results_dir),
            "target_url": target_url,
            "target_parameters": target_parameters,
            "num_questions": num_questions,
        }
        parameters_file.write(json.dumps(parameters, indent=4))
    logger.info("Evaluation results saved in %s", results_dir)
    return True


def process_config(obj: dict):
    """Replace special markers in a config dict with their values:
    * <TIMESTAMP> with current timestamp
    * <READFILE> with contents of file
    """
    if isinstance(obj, dict):
        for key in obj:
            if isinstance(obj[key], dict):
                process_config(obj[key])
            elif isinstance(obj[key], str) and "<TIMESTAMP>" in obj[key]:
                logger.info("Replaced %s in config with timestamp", key)
                obj[key] = obj[key].replace("<TIMESTAMP>", str(int(time.time())))
            elif isinstance(obj[key], str) and "<READFILE>" in obj[key]:
                with open(obj[key].replace("<READFILE>", ""), encoding="utf-8") as f:
                    logger.info("Replaced %s in config with contents of %s", key, f.name)
                    obj[key] = f.read()


def run_evaluate_from_config(
    working_dir,
    config_path,
    num_questions=None,
    target_url=None,
    results_dir=None,
    openai_config=None,
    model=None,
    azure_credential=None,
):
    config_path = working_dir / Path(config_path)
    logger.info("Running evaluation from config %s", config_path)
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
        process_config(config)

    if results_dir is None:
        results_dir = working_dir / Path(config["results_dir"])

    evaluation_run_complete = run_evaluation(
        openai_config=openai_config or service_setup.get_openai_config(),
        testdata_path=working_dir / config["testdata_path"],
        results_dir=results_dir,
        target_url=target_url or config["target_url"],
        target_parameters=config.get("target_parameters", {}),
        num_questions=num_questions,
        requested_metrics=config.get(
            "requested_metrics",
            ["gpt_groundedness", "gpt_relevance", "gpt_coherence", "answer_length", "latency"],
        ),
        target_response_answer_jmespath=config.get("target_response_answer_jmespath", "output_text"),
        target_response_context_jmespath=config.get("target_response_context_jmespath", "context.data_points.text"),
        model=model,
        azure_credential=azure_credential,
    )

    if evaluation_run_complete:
        results_config_path = results_dir / "config.json"
        logger.info("Saving original config file back to to %s", results_config_path)
        with open(config_path, encoding="utf-8") as input_config:
            with open(results_config_path, "w", encoding="utf-8") as output_config:
                output_config.write(input_config.read())
    else:
        logger.error("Evaluation was terminated early due to an error ⬆")
