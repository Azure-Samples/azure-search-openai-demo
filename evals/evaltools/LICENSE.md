# Attribution

The code in this `evaltools` package is a vendored subset of the
[ai-rag-chat-evaluator](https://github.com/Azure-Samples/ai-rag-chat-evaluator)
project, copied into this repository so it can be maintained alongside the eval
scripts (notably to support reasoning models via `is_reasoning_model=True`).

Original project license:

```
MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Local changes

- Kept only the evaluation runner (`eval/`), service setup helpers
  (`service_setup.py`), and the markdown reviewers (`review/`).
- Removed the synthetic-data generation module (`gen/`) and the Textual TUI
  reviewers (`*_app.py`).
- `eval/evaluate_metrics/builtin_metrics.py`: the LLM-judged evaluators are now
  constructed with `is_reasoning_model=True` so they send
  `max_completion_tokens` instead of `max_tokens`, which is required by
  reasoning models such as gpt-5.
- `eval/evaluate_metrics/__init__.py`: dropped the promptflow-based prompt
  metrics (unused here), removing the promptflow/numpy dependencies.
- Internal imports converted to relative imports.
- The CLI (`cli.py`) keeps only the `summary` and `diff` commands, which always
  emit markdown.
