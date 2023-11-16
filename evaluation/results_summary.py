import json
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, TextArea


class ParametersScreen(ModalScreen):
    CSS_PATH = "parameters_screen.tcss"

    def __init__(self, folder, parameters) -> None:
        super().__init__()
        self.folder = folder
        self.parameters = parameters

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"Parameters for: {self.folder}", id="header"),
            TextArea(json.dumps(self.parameters, indent=4), language="json", id="body"),
            Button("Close", variant="primary", id="button"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()


class TableApp(App):
    def __init__(self) -> None:
        super().__init__()
        self.rows = [
            ("folder", "groundedness", "%", "relevance", "%", "coherence", "%", "citation %", "length"),
        ]
        self.row_parameters = {}
        results_dir = Path(__file__).parent.absolute() / "results"
        folders = [f for f in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, f))]
        for folder in folders:
            with open(Path(results_dir) / folder / "summary.json") as f:
                summary = json.load(f)
                groundedness = summary["gpt_groundedness"]
                relevance = summary["gpt_relevance"]
                coherence = summary["gpt_coherence"]
                citation = summary.get("answer_has_citation", {}).get("rate", "Unknown")
                self.rows.append(
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
            with open(Path(results_dir) / folder / "parameters.json") as f:
                self.row_parameters[folder] = json.load(f)

    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*self.rows[0])
        table.add_rows(self.rows[1:])

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        if event.coordinate.column == 0:
            folder = event.value
            parameters = self.row_parameters[folder]
            self.push_screen(ParametersScreen(folder, parameters))


app = TableApp()
if __name__ == "__main__":
    app.run()
