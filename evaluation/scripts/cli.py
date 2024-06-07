import logging
from pathlib import Path

import dotenv
import typer
from rich.logging import RichHandler

from . import service_setup
from .evaluate import run_evaluate_from_config
from .generate import generate_dontknows_qa_data, generate_test_qa_data

app = typer.Typer(pretty_exceptions_enable=False)

logging.basicConfig(
    level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("scripts")
# We only set the level to INFO for our logger,
# to avoid seeing the noisy INFO level logs from the Azure SDKs
logger.setLevel(logging.INFO)

dotenv.load_dotenv(override=True)


def int_or_none(raw: str) -> int | None:
    return None if raw == "None" else int(raw)


def str_or_none(raw: str) -> str | None:
    return None if raw == "None" else raw


@app.command()
def evaluate(
    config: Path = typer.Option(
        exists=True, dir_okay=False, file_okay=True, help="Path to config.json", default="config.json"
    ),
    numquestions: int | None = typer.Option(
        help="Number of questions to evaluate (defaults to all if not specified).", default=None, parser=int_or_none
    ),
    targeturl: str | None = typer.Option(
        help="URL of the target service to evaluate against (defaults to the one in the config).",
        default=None,
        parser=str_or_none,
    ),
):
    run_evaluate_from_config(Path.cwd(), config, numquestions, targeturl)


@app.command()
def generate(
    output: Path = typer.Option(exists=False, dir_okay=False, file_okay=True),
    numquestions: int = typer.Option(help="Number of questions to generate", default=200),
    persource: int = typer.Option(help="Number of questions to generate per source", default=5),
):
    generate_test_qa_data(
        openai_config=service_setup.get_openai_config_dict(),
        search_client=service_setup.get_search_client(),
        num_questions_total=numquestions,
        num_questions_per_source=persource,
        output_file=Path.cwd() / output,
    )


# @app.command()
# def generate_dontknows(
#     input: Path = typer.Option(exists=True, dir_okay=False, file_okay=True),
#     output: Path = typer.Option(exists=False, dir_okay=False, file_okay=True),
#     numquestions: int = typer.Option(help="Number of questions to generate", default=40),
# ):
#     generate_dontknows_qa_data(
#         openai_config=service_setup.get_openai_config(),
#         num_questions_total=numquestions,
#         input_file=Path.cwd() / input,
#         output_file=Path.cwd() / output,
#     )


def cli():
    app()
