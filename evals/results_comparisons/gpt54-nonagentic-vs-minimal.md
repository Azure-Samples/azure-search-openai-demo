# Eval Comparison Summary

## Group Summary

| Group | Runs | Questions | Config consistent | Test data |
|---|---:|---:|---|---|
| non-agentic | 1 | 50 | True | ground_truth.jsonl |
| minimal | 1 | 50 | True | ground_truth.jsonl |

## Metrics

| Group | Metric | Mean | 95% CI | n |
|---|---|---:|---|---:|
| non-agentic | gpt_groundedness.pass_rate | 0.9600 | [0.9000, 1.0000] | 50 |
| non-agentic | gpt_groundedness.mean_rating | 4.6800 | [4.4800, 4.8400] | 50 |
| non-agentic | gpt_relevance.pass_rate | 0.9600 | [0.9000, 1.0000] | 50 |
| non-agentic | gpt_relevance.mean_rating | 4.2600 | [4.1200, 4.4000] | 50 |
| non-agentic | answer_length.mean | 632.8200 | [555.3600, 712.7000] | 50 |
| non-agentic | latency.mean | 3.8346 | [3.3511, 4.5101] | 50 |
| non-agentic | citations_matched.rate | 0.4700 | [0.3500, 0.5900] | 50 |
| non-agentic | any_citation.rate | 0.9800 | [0.9400, 1.0000] | 50 |
| minimal | gpt_groundedness.pass_rate | 0.9600 | [0.9000, 1.0000] | 50 |
| minimal | gpt_groundedness.mean_rating | 4.6600 | [4.4600, 4.8400] | 50 |
| minimal | gpt_relevance.pass_rate | 0.9800 | [0.9400, 1.0000] | 50 |
| minimal | gpt_relevance.mean_rating | 4.2400 | [4.1000, 4.3800] | 50 |
| minimal | answer_length.mean | 695.0400 | [607.3400, 793.8400] | 50 |
| minimal | latency.mean | 3.9298 | [3.5886, 4.3488] | 50 |
| minimal | citations_matched.rate | 0.5000 | [0.3900, 0.6100] | 50 |
| minimal | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |

## Comparisons Vs Reference

| Candidate | Metric | Baseline mean | Candidate mean | Delta | 95% CI for delta | p-value | Significant | Paired questions |
|---|---|---:|---:|---:|---|---:|---|---:|
| minimal | gpt_groundedness.pass_rate | 0.9600 | 0.9600 | 0.0000 | [-0.0800, 0.0800] | 1.0000 | False | 50 |
| minimal | gpt_groundedness.mean_rating | 4.6800 | 4.6600 | -0.0200 | [-0.2800, 0.2000] | 1.0000 | False | 50 |
| minimal | gpt_relevance.pass_rate | 0.9600 | 0.9800 | 0.0200 | [-0.0400, 0.0800] | 1.0000 | False | 50 |
| minimal | gpt_relevance.mean_rating | 4.2600 | 4.2400 | -0.0200 | [-0.2000, 0.1800] | 1.0000 | False | 50 |
| minimal | answer_length.mean | 632.8200 | 695.0400 | 62.2200 | [-4.2600, 134.3600] | 0.0794 | False | 50 |
| minimal | latency.mean | 3.8346 | 3.9298 | 0.0952 | [-0.5043, 0.6602] | 0.7700 | False | 50 |
| minimal | citations_matched.rate | 0.4700 | 0.5000 | 0.0300 | [-0.0300, 0.0900] | 0.5034 | False | 50 |
| minimal | any_citation.rate | 0.9800 | 1.0000 | 0.0200 | [0.0000, 0.0600] | 1.0000 | False | 50 |
