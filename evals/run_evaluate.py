import argparse
import logging
import os
from pathlib import Path

from azure.identity import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from rich.logging import RichHandler

from evaltools.eval.evaluate import run_evaluate_from_config

logger = logging.getLogger("ragapp")


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

    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    if AZURE_TENANT_ID:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential with tenant_id %s", AZURE_TENANT_ID)
        azure_credential = AzureDeveloperCliCredential(tenant_id=AZURE_TENANT_ID, process_timeout=60)
    else:
        logger.info("Setting up Azure credential using AzureDeveloperCliCredential for home tenant")
        azure_credential = AzureDeveloperCliCredential(process_timeout=60)

    openai_config = {
        "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
        "azure_deployment": os.environ["AZURE_OPENAI_EVAL_DEPLOYMENT"],
    }

    run_evaluate_from_config(
        working_dir=Path(__file__).parent,
        config_path="evaluate_config.json",
        num_questions=args.numquestions,
        target_url=args.targeturl,
        results_dir=args.resultsdir,
        openai_config=openai_config,
        model=os.environ["AZURE_OPENAI_EVAL_MODEL"],
        azure_credential=azure_credential,
    )
