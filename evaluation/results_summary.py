import json
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import DataTable

ROWS = [
    ("folder", "groundedness", "%", "relevance", "%", "coherence", "%", "citation %", "length"),
]


results_dir = Path(__file__).parent.absolute() / "results"
folders = [f for f in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, f))]
for folder in folders:
    with open(Path(results_dir) / folder / "summary.json") as f:
        summary = json.load(f)
        groundedness = summary["gpt_groundedness"]
        relevance = summary["gpt_relevance"]
        coherence = summary["gpt_coherence"]
        citation = summary.get("answer_has_citation", {}).get("rate", "Unknown")
        ROWS.append(
            (
                folder,
                groundedness["mean_rating"],
                groundedness["pass_rate"],
                relevance["mean_rating"],
                relevance["pass_rate"],
                coherence["mean_rating"],
                coherence["pass_rate"],
                citation,
                summary.get("answer_length", {}).get("mean", "Unknown"),
            )
        )


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])


app = TableApp()
if __name__ == "__main__":
    app.run()
