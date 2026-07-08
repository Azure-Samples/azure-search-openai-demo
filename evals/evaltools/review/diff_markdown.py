from pathlib import Path
from typing import Any

from .utils import diff_directories


def _round_metric(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 1)
    return value


def main(directories: list[Path], changed: str | None = None):
    data_dicts = diff_directories(directories, changed)

    markdown_str = ""
    for question in data_dicts[0].keys():
        markdown_str += f"**{question}**\n\n"
        # now make an HTML table with the answers
        markdown_str += "<table>\n"
        markdown_str += (
            "<tr><th></th>"
            + "".join([f"<th>{directory.name}</th>" for directory in directories])
            + "<th>ground_truth</th></tr>\n"
        )
        markdown_str += (
            "<tr><th>answer</th>"
            + "".join([f"<td>{data_dict[question]['answer']}</td>" for data_dict in data_dicts])
            + f"<td>{data_dicts[0][question]['truth']}</td></tr>\n"
        )

        # now make rows for each metric
        metrics = {}
        question_results = data_dicts[0][question]
        for column, value in question_results.items():
            if isinstance(value, int | float):
                metrics[column] = []
        for metric_name in metrics.keys():
            first_value = _round_metric(data_dicts[0][question].get(metric_name))
            for ind, data_dict in enumerate(data_dicts):
                value = _round_metric(data_dict[question].get(metric_name))
                # Insert arrow emoji based on the difference between metric value and the first data_dict
                value_emoji = ""
                if value is not None and ind > 0 and value != first_value:
                    value_emoji = "⬆️" if value > data_dicts[0][question][metric_name] else "⬇️"
                metrics[metric_name].append(f"{value} {value_emoji}")
        # make a row for each metric
        for metric_name, metric_values in metrics.items():
            markdown_str += (
                f"<tr><th>{metric_name}</th>"
                + "".join([f"<td>{value}</td>" for value in metric_values])
                + "<td>N/A</td></tr>\n"
            )
        markdown_str += "</table>\n\n"
    return markdown_str
