import argparse
import logging
import os
from pathlib import Path

from azure.identity import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from evaltools.eval.evaluate import run_evaluate_from_config
from rich.logging import RichHandler

logger = logging.getLogger("ragapp")


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
        level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
    )
    load_azd_env()

    parser = argparse.ArgumentParser(description="Run evaluation with OpenAI configuration.")
    parser.add_argument("--targeturl", type=str, help="Specify the target URL.")
    parser.add_argument("--resultsdir", type=Path, help="Specify the results directory.")
    parser.add_argument("--numquestions", type=int, help="Specify the number of questions.")

    args = parser.parse_args()

    openai_config = get_openai_config()

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
