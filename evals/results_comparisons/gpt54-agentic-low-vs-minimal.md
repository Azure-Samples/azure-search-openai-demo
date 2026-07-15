# Eval Comparison Summary

## Group Summary

| Group | Runs | Questions | Config consistent | Test data |
|---|---:|---:|---|---|
| low | 1 | 50 | True | ground_truth.jsonl |
| minimal | 1 | 50 | True | ground_truth.jsonl |

## Metrics

| Group | Metric | Mean | 95% CI | n |
|---|---|---:|---|---:|
| low | gpt_groundedness.pass_rate | 0.9800 | [0.9400, 1.0000] | 50 |
| low | gpt_groundedness.mean_rating | 4.6800 | [4.5400, 4.8200] | 50 |
| low | gpt_relevance.pass_rate | 0.9400 | [0.8600, 1.0000] | 50 |
| low | gpt_relevance.mean_rating | 4.2200 | [4.0800, 4.3600] | 50 |
| low | answer_length.mean | 667.1800 | [579.2600, 756.8600] | 50 |
| low | latency.mean | 17.4657 | [16.1791, 18.5477] | 50 |
| low | citations_matched.rate | 0.4200 | [0.3100, 0.5300] | 50 |
| low | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |
| minimal | gpt_groundedness.pass_rate | 0.9400 | [0.8600, 1.0000] | 50 |
| minimal | gpt_groundedness.mean_rating | 4.6400 | [4.4200, 4.8200] | 50 |
| minimal | gpt_relevance.pass_rate | 0.9400 | [0.8600, 1.0000] | 50 |
| minimal | gpt_relevance.mean_rating | 4.2200 | [4.0600, 4.3800] | 50 |
| minimal | answer_length.mean | 680.7200 | [588.7600, 782.8800] | 50 |
| minimal | latency.mean | 18.7074 | [16.9850, 20.3843] | 50 |
| minimal | citations_matched.rate | 0.4900 | [0.3800, 0.6000] | 50 |
| minimal | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |

## Comparisons Vs Reference

| Candidate | Metric | Baseline mean | Candidate mean | Delta | 95% CI for delta | p-value | Significant | Paired questions |
|---|---|---:|---:|---:|---|---:|---|---:|
| minimal | gpt_groundedness.pass_rate | 0.9800 | 0.9400 | -0.0400 | [-0.1000, 0.0000] | 0.4956 | False | 50 |
| minimal | gpt_groundedness.mean_rating | 4.6800 | 4.6400 | -0.0400 | [-0.2200, 0.1200] | 0.8232 | False | 50 |
| minimal | gpt_relevance.pass_rate | 0.9400 | 0.9400 | 0.0000 | [0.0000, 0.0000] | 1.0000 | False | 50 |
| minimal | gpt_relevance.mean_rating | 4.2200 | 4.2200 | 0.0000 | [-0.1200, 0.1200] | 1.0000 | False | 50 |
| minimal | answer_length.mean | 667.1800 | 680.7200 | 13.5400 | [-41.9400, 69.7800] | 0.6446 | False | 50 |
| minimal | latency.mean | 17.4657 | 18.7074 | 1.2418 | [0.0715, 2.5234] | 0.0552 | False | 50 |
| minimal | citations_matched.rate | 0.4200 | 0.4900 | 0.0700 | [-0.0100, 0.1600] | 0.1738 | False | 50 |
| minimal | any_citation.rate | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] | 1.0000 | False | 50 |
