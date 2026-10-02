# Data Model: Agent Guard

**Source**: [spec.md](spec.md), especially FR-07–FR-34 and AC-32–AC-34. This is a design contract, not a claim that classes or storage exist.

## PolicySet and CheckPolicy

`PolicySet` is immutable after preparation. It has a stable policy identity, settings fingerprint, ordered check policies, and an independent `evidence_required` setting. Its default contains required local PII at input and output only. A `CheckPolicy` identifies one of six check kinds, its valid boundary or boundaries, required or optional status, criteria/rubric version, and a confidence minimum only when the check produces valid semantic confidence. Enabled check identities are unique within a set.

Preparation validates settings, local dependencies, model assets, and presence of credentials for enabled checks. Disabled checks impose no such requirements. Missing setup is a configuration failure even for an optional check. The settings fingerprint is derived from non-secret configuration; credentials and raw criteria containing user content do not appear in diagnostics.

## EvaluationContext and NativeSnapshot

`EvaluationContext` is request-local. It holds a request identifier, current request, relevant conversation, candidate answer when present, associated evidence, active policy identity, and boundary. The host supplies the current request, evidence identity, and final-answer declaration. Contexts are never shared across concurrent requests.

`NativeSnapshot` is an adapter-owned, immutable view of the content that will cross a protected boundary. It records framework, native execution surface, boundary, message roles and ordered text parts, model-bound textual tool descriptions, recursively discovered string keys and values in JSON-compatible tool arguments, evidence identifiers, and its request-local association with a model call. The native object itself remains caller/framework owned and is returned unchanged when permitted.

The snapshot must cover exactly the assembled model-bound content at each input boundary, or the final answer and any output-evaluation context at an output boundary. A changed snapshot after an earlier check requires another check before submission. If adapter placement cannot observe a known later mutation, the arrangement is rejected at setup. Unknown or opaque model-bound content is unsupported, never ignored or stringified.

| Content form | v1 handling |
| --- | --- |
| Text strings or native text parts in system, developer where exposed, user, assistant, and tool messages | Preserve role and order; inspect every text part. |
| Retrieved evidence text and model-bound tool descriptions | Inspect before external disclosure; preserve source association. |
| JSON-compatible tool arguments | Preserve structure; inspect all string keys and values, including nested keys and values. Numeric and Boolean values are retained without text inspection. |
| Images, audio, video, binary attachments, opaque model-bound objects | Reject explicitly as unsupported. |

The assembled context is limited to 100,000 Unicode code points of supported text, 128 messages, and 64 evidence items. Count without Unicode normalization and include string tool-argument keys. Equality with one limit is valid only if all other limits pass. The external provider additionally limits serialized requests to 512 KiB and responses to 256 KiB. Overflow is reported before affected disclosure, with no truncation.

## EvidenceItem

An `EvidenceItem` contains an identifier unique within the request, supported source text, a provenance reference held by the caller, and an association with the answer-generation step. Conversation messages and arbitrary tool output are not evidence by default. Groundedness may be skipped when the evidence set is empty; a separately required evidence condition still blocks delivery.

## CheckResult and BoundaryDecision

`CheckResult` contains check identity, boundary, one outcome (`pass`, `violation`, `inconclusive`, `evaluation_error`, or `skipped`), a sanitized reason code, elapsed time, available confidence, evaluator identity/version when available, and optional usage/cost or error category. Unavailable cost is unknown, not zero. An unrun check after an early block is represented as skipped/not evaluated, never passed.

`BoundaryDecision` contains request and policy identities, boundary, ordered check results, aggregate `allow` or `block`, and a sanitized blocking reason. Required violations, inconclusive results, and evaluation errors block. Optional results cannot reverse a required block. A missing-evidence skip is governed by the independent evidence requirement. Live enforcement raises a distinguishable exception for a block; saved-example evaluation records the same decision without aborting the dataset.

Configuration and integration failures are outside `CheckResult`. A known unsupported native arrangement fails configuration before execution. An unexpected adapter extraction, boundary-identification, or native result/state-preservation fault is an integration failure and stops affected submission or delivery regardless of optional policy status. Caller errors and cancellation retain their native meaning.

## SavedExample, ReferenceLabel, and EvaluationReport

`SavedExample` has a stable example identifier, current request, optional conversation, candidate answer, optional evidence, and optional independent labels. A `ReferenceLabel` is scoped to `(example_id, policy_id, boundary)` and is `pass` or `violation`; absence means unknown. Duplicate identifiers or malformed records are invalid, with individual-record failures represented by sanitized error records when the global policy is valid.

`EvaluationReport` contains per-example check results and decisions, policy/settings and evaluator identities, counts by outcome, classified and label coverage, independently justified quality ratios, and measured overhead/available cost. Reports exclude raw request/answer/evidence text, detected PII values, credentials, arbitrary evaluator rationale, and content hashes. Undefined ratios remain undefined. Comparison joins two runs on stable example identifiers and reports changed decisions without changing live policy.

## Lifecycle and Relationships

```text
PolicySet --prepare--> PreparedGuard --close--> ClosedGuard
PreparedGuard + EvaluationContext --extract--> NativeSnapshot
NativeSnapshot --validate and local PII--> remote checks when enabled
check results --reduce--> BoundaryDecision
BoundaryDecision --allow--> one native handoff or unchanged final return
BoundaryDecision --block--> typed policy exception or offline blocked record
```

Preparation failure prevents protected work. A runtime integration failure also prevents the affected handoff or delivery, but does not claim rollback of earlier tool actions, state persistence, or model cost. Every new model submission gets its own input snapshot and decision. Final output checks apply to direct and retrieval answer paths, not intermediate tool requests.
