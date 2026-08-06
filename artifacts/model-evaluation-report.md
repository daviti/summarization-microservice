# Candidate Model Evaluation

## Evaluation criteria

- Safety performance (rate of correctly refusing policy-violating content)
- Valid-content utility (quality/usefulness of summaries on safe input)

`project_inputs/candidate_model_runs.json` only reports `safety_pass_rate`
and `utility_score` for each run; it does not include refusal accuracy,
summary quality, latency, or error rate as separate fields, so this
evaluation is scoped to the two metrics actually present in the data.

## Candidate comparison

| Run ID | Safety pass rate | Utility score | Decision |
|---|---:|---:|---|
| model_run_001 | 0.92 | 0.81 | Selected |
| model_run_002 | 0.88 | 0.89 | Rejected |

## Selected run

Selected run ID: **model_run_001**

## Rationale

This service's primary job is refusing harmful, illicit, and financial
content before it ever reaches summarization — a false negative here (an
unsafe request that gets summarized instead of refused) is a materially
worse outcome than a lower-quality summary on a safe request. On that
basis, safety_pass_rate is weighted as the primary criterion.

model_run_001 leads on safety (0.92 vs. 0.88), a 4-point gap, while
trailing model_run_002 on utility by 8 points (0.81 vs. 0.89). Both
utility scores are within a reasonable range for a "concise first
sentence" style summarizer, and the utility gap is not large enough to
justify accepting more unsafe passes for it. model_run_001 offers the
better balance of safety and usefulness for this project.

If future candidate runs report additional metrics (refusal accuracy,
summary quality, latency, error rate), re-run this comparison with the
fuller metric set before re-confirming the selection.
