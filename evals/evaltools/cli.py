import logging
from pathlib import Path

import dotenv
import typer
from rich.logging import RichHandler

from .review import diff_markdown, summary_markdown

app = typer.Typer(pretty_exceptions_enable=False)

logging.basicConfig(
    level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("evaltools")
# We only set the level to INFO for our logger,
# to avoid seeing the noisy INFO level logs from the Azure SDKs
logger.setLevel(logging.INFO)

dotenv.load_dotenv(override=True)


def str_or_none(value: str) -> str | None:
    return value if value != "None" else None


@app.command()
def diff(
    directory1: Path = typer.Argument(exists=True, dir_okay=True, file_okay=False),
    directory2: Path | None = typer.Argument(default=None, exists=True, dir_okay=True, file_okay=False),
    changed: str | None = typer.Option(
        help="Show only questions whose values changed for the given column", default=None, parser=str_or_none
    ),
):
    directories = [directory1] if directory2 is None else [directory1, directory2]
    print(diff_markdown.main(directories, changed))


@app.command()
def summary(
    results_dir: Path = typer.Argument(exists=True, dir_okay=True, file_okay=False),
    highlight: str | None = typer.Option(
        help="Highlight a specific run in the summary", default=None, parser=str_or_none
    ),
):
    print(summary_markdown.main(results_dir, highlight_run=highlight))


def cli():
    app()
