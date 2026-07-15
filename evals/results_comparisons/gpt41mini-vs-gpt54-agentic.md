# Eval Comparison Summary

## Group Summary

| Group | Runs | Questions | Config consistent | Test data |
|---|---:|---:|---|---|
| gpt41mini-agentic | 1 | 50 | True | ground_truth.jsonl |
| gpt54-agentic | 1 | 50 | True | ground_truth.jsonl |

## Metrics

| Group | Metric | Mean | 95% CI | n |
|---|---|---:|---|---:|
| gpt41mini-agentic | gpt_groundedness.pass_rate | 0.9600 | [0.9000, 1.0000] | 50 |
| gpt41mini-agentic | gpt_groundedness.mean_rating | 4.6200 | [4.4200, 4.8000] | 50 |
| gpt41mini-agentic | gpt_relevance.pass_rate | 0.9200 | [0.8400, 0.9800] | 50 |
| gpt41mini-agentic | gpt_relevance.mean_rating | 4.1800 | [4.0200, 4.3400] | 50 |
| gpt41mini-agentic | answer_length.mean | 679.6800 | [587.2800, 780.8800] | 50 |
| gpt41mini-agentic | latency.mean | 17.7399 | [16.3911, 18.8998] | 50 |
| gpt41mini-agentic | citations_matched.rate | 0.5100 | [0.4000, 0.6200] | 50 |
| gpt41mini-agentic | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |
| gpt54-agentic | gpt_groundedness.pass_rate | 0.9800 | [0.9400, 1.0000] | 50 |
| gpt54-agentic | gpt_groundedness.mean_rating | 4.6800 | [4.5400, 4.8200] | 50 |
| gpt54-agentic | gpt_relevance.pass_rate | 0.9400 | [0.8600, 1.0000] | 50 |
| gpt54-agentic | gpt_relevance.mean_rating | 4.2200 | [4.0800, 4.3600] | 50 |
| gpt54-agentic | answer_length.mean | 667.1800 | [579.2600, 756.8600] | 50 |
| gpt54-agentic | latency.mean | 17.4657 | [16.1791, 18.5477] | 50 |
| gpt54-agentic | citations_matched.rate | 0.4200 | [0.3100, 0.5300] | 50 |
| gpt54-agentic | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |

## Comparisons Vs Reference

| Candidate | Metric | Baseline mean | Candidate mean | Delta | 95% CI for delta | p-value | Significant | Paired questions |
|---|---|---:|---:|---:|---|---:|---|---:|
| gpt54-agentic | gpt_groundedness.pass_rate | 0.9600 | 0.9800 | 0.0200 | [-0.0400, 0.1000] | 1.0000 | False | 50 |
| gpt54-agentic | gpt_groundedness.mean_rating | 4.6200 | 4.6800 | 0.0600 | [-0.1000, 0.2400] | 0.6416 | False | 50 |
| gpt54-agentic | gpt_relevance.pass_rate | 0.9200 | 0.9400 | 0.0200 | [-0.0400, 0.1000] | 1.0000 | False | 50 |
| gpt54-agentic | gpt_relevance.mean_rating | 4.1800 | 4.2200 | 0.0400 | [-0.1000, 0.1800] | 0.7918 | False | 50 |
| gpt54-agentic | answer_length.mean | 679.6800 | 667.1800 | -12.5000 | [-71.1000, 41.0800] | 0.6604 | False | 50 |
| gpt54-agentic | latency.mean | 17.7399 | 17.4657 | -0.2742 | [-1.1248, 0.5515] | 0.5334 | False | 50 |
| gpt54-agentic | citations_matched.rate | 0.5100 | 0.4200 | -0.0900 | [-0.1700, -0.0200] | 0.0458 | True | 50 |
| gpt54-agentic | any_citation.rate | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] | 1.0000 | False | 50 |
