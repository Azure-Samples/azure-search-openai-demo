# a CLI tool to diff two JSON files

import argparse
import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Markdown, Static


class DiffApp(App):
    CSS_PATH = "diff_app.tcss"

    def __init__(self, directory1: Path, directory2: Path):
        super().__init__()
        self.directory1 = directory1
        self.directory2 = directory2
        self.data1_dict = {}
        self.data2_dict = {}
        with open(self.directory1 / "eval_results.jsonl") as f:
            self.data1 = [json.loads(question_json) for question_json in f.readlines()]
            self.data1_dict = {question["question"]: question for question in self.data1}
        with open(self.directory2 / "eval_results.jsonl") as f:
            self.data2 = [json.loads(question_json) for question_json in f.readlines()]
            self.data2_dict = {question["question"]: question for question in self.data2}
        self.current_question = 0

    def on_mount(self):
        self.next_question()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.exit()
        else:
            self.next_question()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(id="question")
            with Horizontal(id="sources"):
                yield Static(self.directory1.name, classes="source")
                yield Static(self.directory2.name, classes="source")
            with Horizontal(id="answers"):
                with VerticalScroll(classes="answer"):
                    yield Markdown(id="answer1")
                with VerticalScroll(classes="answer"):
                    yield Markdown(id="answer2")
            with Horizontal(id="buttons"):
                yield Button.success("Next question", classes="button")
                yield Button.error("Quit", id="quit", classes="button")

    def next_question(self):
        question = self.data1[self.current_question]
        self.query_one("#question", Static).update(question["question"])
        self.query_one("#answer1", Markdown).update(question["answer"])
        self.query_one("#answer2", Markdown).update(self.data2_dict[question["question"]]["answer"])
        self.current_question += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diff two JSON files")
    parser.add_argument("directory1", help="First directory")
    parser.add_argument("directory2", help="Second directory")
    args = parser.parse_args()
    EVAL_DIR = Path(__file__).parent.absolute() / "results"

    app = DiffApp(EVAL_DIR / args.directory1, EVAL_DIR / args.directory2)
    app.run()
