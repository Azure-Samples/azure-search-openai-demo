import argparse
import logging
import os
import re
from pathlib import Path

from azure.identity import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from evaltools.eval.evaluate import run_evaluate_from_config
from evaltools.eval.evaluate_metrics import register_metric
from evaltools.eval.evaluate_metrics.base_metric import BaseMetric
from rich.logging import RichHandler

logger = logging.getLogger("ragapp")


class AnyCitationMetric(BaseMetric):
    METRIC_NAME = "any_citation"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def any_citation(*, response, **kwargs):
            if response is None:
                logger.warning("Received response of None, can't compute any_citation metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            return {cls.METRIC_NAME: bool(re.search(r"\[([^\]]+)\.\w{3,4}(#page=\d+)*\]", response))}

        return any_citation

    @classmethod
    def get_aggregate_stats(cls, df):
        df = df[df[cls.METRIC_NAME] != -1]
        return {
            "total": int(df[cls.METRIC_NAME].sum()),
            "rate": round(df[cls.METRIC_NAME].mean(), 2),
        }


class CitationsMatchedMetric(BaseMetric):
    METRIC_NAME = "citations_matched"

    @classmethod
    def evaluator_fn(cls, **kwargs):
        def citations_matched(*, response, ground_truth, **kwargs):
            if response is None:
                logger.warning("Received response of None, can't compute citation_match metric. Setting to -1.")
                return {cls.METRIC_NAME: -1}
            # Return true if all citations in the truth are present in the response
            truth_citations = set(re.findall(r"\[([^\]]+)\.\w{3,4}(#page=\d+)*\]", ground_truth))
            response_citations = set(re.findall(r"\[([^\]]+)\.\w{3,4}(#page=\d+)*\]", response))
            # Count the percentage of citations that are present in the response
            num_citations = len(truth_citations)
            num_matched_citations = len(truth_citations.intersection(response_citations))
            return {cls.METRIC_NAME: num_matched_citations / num_citations}

        return citations_matched

    @classmethod
    def get_aggregate_stats(cls, df):
        df = df[df[cls.METRIC_NAME] != -1]
        return {
            "total": int(df[cls.METRIC_NAME].sum()),
            "rate": round(df[cls.METRIC_NAME].mean(), 2),
        }


def get_openai_config():
    azure_endpoint = f"https://{os.getenv('AZURE_OPENAI_SERVICE')}.openai.azure.com"
    azure_deployment = os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"]
    openai_config = {"azure_endpoint": azure_endpoint, "azure_deployment": azure_deployment}
    # azure-ai-evaluate will call DefaultAzureCredential behind the scenes,
    # so we must be logged in to Azure CLI with the correct tenant
    return openai_config


def get_azure_credential():
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    if AZURE_TENANT_ID:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential with tenant_id %s", AZURE_TENANT_ID)
        azure_credential = AzureDeveloperCliCredential(tenant_id=AZURE_TENANT_ID, process_timeout=60)
    else:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential for home tenant")
        azure_credential = AzureDeveloperCliCredential(process_timeout=60)
    return azure_credential


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger.setLevel(logging.INFO)
    logging.getLogger("evaltools").setLevel(logging.INFO)
    load_azd_env()

    parser = argparse.ArgumentParser(description="Run evaluation with OpenAI configuration.")
    parser.add_argument("--targeturl", type=str, help="Specify the target URL.")
    parser.add_argument("--resultsdir", type=Path, help="Specify the results directory.")
    parser.add_argument("--numquestions", type=int, help="Specify the number of questions.")

    args = parser.parse_args()

    openai_config = get_openai_config()

    register_metric(CitationsMatchedMetric)
    register_metric(AnyCitationMetric)

    run_evaluate_from_config(
        working_dir=Path(__file__).parent,
        config_path="evaluate_config.json",
        num_questions=args.numquestions,
        target_url=args.targeturl,
        results_dir=args.resultsdir,
        openai_config=openai_config,
        model=os.environ["AZURE_OPENAI_EVAL_MODEL"],
        azure_credential=get_azure_credential(),
    )
