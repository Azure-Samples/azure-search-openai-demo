from pathlib import Path

from .utils import summarize_results


def main(results_dir: Path, highlight_run: str | None = None) -> str:
    rows, row_parameters = summarize_results(results_dir)
    # transpose the rows
    rows = list(map(list, zip(*rows)))

    # make a markdown table
    headers = ["metric", "stat"] + list(row_parameters.keys())
    # find the index of the highlight run
    if highlight_run:
        highlight_run = highlight_run.strip()
        highlight_run_index = headers.index(highlight_run)
    else:
        highlight_run_index = None

    # put a star and bold the highlight run
    if highlight_run:
        headers = [f"☞{header}☜" if ind == highlight_run_index else header for ind, header in enumerate(headers)]

    table = "| " + " | ".join(headers) + " |\n"
    table += "|" + " |".join(["---"] * len(rows[0])) + " |\n"
    for ind, row in enumerate(rows[1:]):
        if row[0] == "":
            row[0] = "↑"
        # stringifying the row
        row = [str(cell) for cell in row]
        # highlight the cell that corresponds to the highlight run
        if highlight_run:
            row = [f"**{cell}**" if ind == highlight_run_index else cell for ind, cell in enumerate(row)]
        table += "| " + " | ".join(row) + " |\n"
    return table
