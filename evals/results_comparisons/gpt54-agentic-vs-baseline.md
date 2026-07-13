# Eval Comparison Summary

## Group Summary

| Group | Runs | Questions | Config consistent | Test data |
|---|---:|---:|---|---|
| baseline | 4 | 50 | True | ground_truth.jsonl |
| agentic-gpt54 | 1 | 50 | True | ground_truth.jsonl |

## Metrics

| Group | Metric | Mean | 95% CI | n |
|---|---|---:|---|---:|
| baseline | gpt_groundedness.pass_rate | 0.9850 | [0.9650, 1.0000] | 50 |
| baseline | gpt_groundedness.mean_rating | 4.8900 | [4.8200, 4.9450] | 50 |
| baseline | gpt_relevance.pass_rate | 0.8950 | [0.8250, 0.9550] | 50 |
| baseline | gpt_relevance.mean_rating | 4.1900 | [4.0700, 4.3050] | 50 |
| baseline | answer_length.mean | 647.7900 | [580.0550, 715.7350] | 50 |
| baseline | latency.mean | 3.5536 | [3.4370, 3.6732] | 50 |
| baseline | citations_matched.rate | 0.5250 | [0.4075, 0.6375] | 50 |
| baseline | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |
| agentic-gpt54 | gpt_groundedness.pass_rate | 0.9800 | [0.9400, 1.0000] | 50 |
| agentic-gpt54 | gpt_groundedness.mean_rating | 4.6800 | [4.5400, 4.8200] | 50 |
| agentic-gpt54 | gpt_relevance.pass_rate | 0.9400 | [0.8600, 1.0000] | 50 |
| agentic-gpt54 | gpt_relevance.mean_rating | 4.2200 | [4.0800, 4.3600] | 50 |
| agentic-gpt54 | answer_length.mean | 667.1800 | [579.2600, 756.8600] | 50 |
| agentic-gpt54 | latency.mean | 17.4657 | [16.1791, 18.5477] | 50 |
| agentic-gpt54 | citations_matched.rate | 0.4200 | [0.3100, 0.5300] | 50 |
| agentic-gpt54 | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |

## Comparisons Vs Reference

| Candidate | Metric | Baseline mean | Candidate mean | Delta | 95% CI for delta | p-value | Significant | Paired questions |
|---|---|---:|---:|---:|---|---:|---|---:|
| agentic-gpt54 | gpt_groundedness.pass_rate | 0.9850 | 0.9800 | -0.0050 | [-0.0550, 0.0300] | 1.0000 | False | 50 |
| agentic-gpt54 | gpt_groundedness.mean_rating | 4.8900 | 4.6800 | -0.2100 | [-0.3600, -0.0700] | 0.0074 | True | 50 |
| agentic-gpt54 | gpt_relevance.pass_rate | 0.8950 | 0.9400 | 0.0450 | [-0.0400, 0.1250] | 0.3608 | False | 50 |
| agentic-gpt54 | gpt_relevance.mean_rating | 4.1900 | 4.2200 | 0.0300 | [-0.1150, 0.1800] | 0.7450 | False | 50 |
| agentic-gpt54 | answer_length.mean | 647.7900 | 667.1800 | 19.3900 | [-47.9250, 80.4750] | 0.5470 | False | 50 |
| agentic-gpt54 | latency.mean | 3.5536 | 17.4657 | 13.9120 | [12.6348, 14.9691] | 0.0000 | True | 50 |
| agentic-gpt54 | citations_matched.rate | 0.5250 | 0.4200 | -0.1050 | [-0.2050, -0.0125] | 0.0416 | True | 50 |
| agentic-gpt54 | any_citation.rate | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] | 1.0000 | False | 50 |
