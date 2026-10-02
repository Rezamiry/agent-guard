# Saved Evaluation and Reporting Contract

**Authority**: [spec.md](../spec.md), FR-20–FR-24, FR-27, and AC-12–AC-26. Offline means evaluating saved examples without generating replacement answers; opt-in remote semantic checks may still require provider access.

## Input dataset

Use UTF-8 JSON Lines, one versioned object per line. Required fields are `schema_version`, `example_id`, `request`, and `candidate_answer`. Optional fields are ordered conversation messages, identified evidence, and independent reference labels. Labels are scoped to `(example_id, policy_id, boundary)` and hold `pass` or `violation`; an omitted label is unknown. Identifiers are unique within a dataset and labels may not be inferred from aggregate decisions. The same supported text forms and size limits as live contexts apply. The caller owns source-file storage and retention.

Invalid global policy setup stops the run before evaluation. An invalid individual line yields a sanitized per-line error record and does not relabel another example or abort the entire dataset. A policy block is an ordinary evaluation decision, not a dataset processing failure. Default dataset traversal is one example at a time; caller-managed concurrency must use independent request contexts.

## Processing and output

Each saved example uses the same policy definitions, local privacy preflight, check-result normalization, and decision reducer as live enforcement. Evaluate the supplied candidate without regeneration. Reports identify schema version, code/policy/settings/evaluator/detector/dataset versions when known, each example ID, per-check boundary and outcome, aggregate allow/block decision, available confidence, elapsed time, error category, and available usage/cost. Absent values are null/unknown, never invented zero. Do not export raw request, answer, evidence, detected PII, credentials, content hashes, arbitrary display labels, or unsupplied evaluator explanations.

Export a sanitized JSON report with per-example records and a CSV aggregate summary. A comparison report joins the same fixed ordered dataset under two policy settings and lists changed per-example decisions and aggregate counts; it does not mutate a live policy. Preserve policy/settings identity on every result. A schema change is versioned and documented with migration guidance.

## Metrics

Separate `pass`, `violation`, `inconclusive`, `evaluation_error`, and `skipped` check outcomes, and aggregate allow/block decisions. For each policy/boundary with independent labels, count true positives, false positives, true negatives, and false negatives only among classified labeled examples. Report labeled coverage, classified coverage, and the denominators of every ratio. Undefined ratios are null/undefined, not zero. Required uncertainty or error can block without becoming a confirmed violation; report aggregate false blocks separately from violation classification.

For AC-25's independent oracle, seven examples include five classified, one error, and one skip. Classified accuracy is 3/5, precision 1/2, recall 1/2, false-positive rate 1/3, and classified coverage 5/7. These numbers come from the spec and must not be recalculated by production metric functions to create their own expected values.

## Release evidence

Predeclare rubrics, labels, datasets, quality gates, and versions before held-out evaluation. Development data may calibrate thresholds; held-out labels are not changed to obtain a pass. Reports distinguish software correctness, local detector quality, and external model judgment quality. Each advertised check includes positive violations and benign near-matches, measured misses and false alarms, overhead and available cost, and stated coverage limits. Deterministic tests need neither network nor API keys; enabled live provider smoke and labeled quality runs remain separate.
