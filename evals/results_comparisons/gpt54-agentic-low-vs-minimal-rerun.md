# Eval Comparison Summary

## Group Summary

| Group | Runs | Questions | Config consistent | Test data |
|---|---:|---:|---|---|
| low | 1 | 50 | True | ground_truth.jsonl |
| minimal | 1 | 50 | True | ground_truth.jsonl |

## Metrics

| Group | Metric | Mean | 95% CI | n |
|---|---|---:|---|---:|
| low | gpt_groundedness.pass_rate | 0.9600 | [0.9000, 1.0000] | 50 |
| low | gpt_groundedness.mean_rating | 4.7000 | [4.5000, 4.8600] | 50 |
| low | gpt_relevance.pass_rate | 0.9800 | [0.9400, 1.0000] | 50 |
| low | gpt_relevance.mean_rating | 4.2200 | [4.1000, 4.3600] | 50 |
| low | answer_length.mean | 697.2600 | [602.5600, 797.4000] | 50 |
| low | latency.mean | 5.6651 | [5.3236, 6.0489] | 50 |
| low | citations_matched.rate | 0.4600 | [0.3500, 0.5800] | 50 |
| low | any_citation.rate | 1.0000 | [1.0000, 1.0000] | 50 |
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
| minimal | gpt_groundedness.mean_rating | 4.7000 | 4.6600 | -0.0400 | [-0.3000, 0.2200] | 0.8782 | False | 50 |
| minimal | gpt_relevance.pass_rate | 0.9800 | 0.9800 | 0.0000 | [-0.0600, 0.0600] | 1.0000 | False | 50 |
| minimal | gpt_relevance.mean_rating | 4.2200 | 4.2400 | 0.0200 | [-0.1000, 0.1400] | 1.0000 | False | 50 |
| minimal | answer_length.mean | 697.2600 | 695.0400 | -2.2200 | [-51.5000, 49.0200] | 0.9314 | False | 50 |
| minimal | latency.mean | 5.6651 | 3.9298 | -1.7353 | [-2.2620, -1.2013] | 0.0000 | True | 50 |
| minimal | citations_matched.rate | 0.4600 | 0.5000 | 0.0400 | [-0.0600, 0.1400] | 0.5810 | False | 50 |
| minimal | any_citation.rate | 1.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] | 1.0000 | False | 50 |
