# Python SDK Contract

**Authority**: [spec.md](../spec.md). This document selects the v1 public operation names for implementation. A change to these names or behaviors requires an updated contract and compatibility review.

## Configuration and lifecycle

The base package imports without framework, PII-model, or provider dependencies. `PolicySet` is immutable and defaults to required local PII on both boundaries. Developers explicitly enable semantic checks and choose valid boundary, criteria, required/optional status, and confidence minimum. Unsupported check/boundary combinations, duplicate identities, non-finite or out-of-range settings, missing enabled dependencies/model assets, or missing required credentials fail preparation. Disabled checks require no resources.

`Guard.prepare()` creates ordinary resources; `await Guard.aprepare()` creates async resources. Protected methods before preparation or after close fail configuration. `close()`/`aclose()` release owned resources. Preparation validates credential presence locally and never probes an external provider. Native Microsoft use is async only even when an ordinary script starts an async main.

## Operations

| Operation | Input | Result |
| --- | --- | --- |
| `evaluate_input` / `aevaluate_input` | PolicySet and request-local assembled context | BoundaryDecision without calling the host answer model. |
| `evaluate_output` / `aevaluate_output` | PolicySet, current request, final candidate, optional identified evidence | BoundaryDecision without rewriting the candidate. |
| `enforce_input` / `aenforce_input` | Same as input evaluation | Returns an allow decision or raises the blocking exception before the affected model handoff. |
| `enforce_output` / `aenforce_output` | Same as output evaluation | Returns the original permitted candidate or raises before delivery. |

Native adapters expose framework-supported entry points and return the framework's original result, metadata, and state on allow. They invoke a protected host operation at most once. A model submission and a final delivery are separate boundaries; a request with several model calls is checked at each model call. An intermediate tool request is not a final answer.

## Exceptions and failure ownership

All library exceptions contain stable sanitized reason codes and no raw conversation, PII value, provider body, credential, or arbitrary host exception text.

| Failure | Public category | Effect |
| --- | --- | --- |
| Invalid policy, absent setup prerequisite, known unsupported native arrangement | `ConfigurationError` | Stop before protected execution. |
| Unsupported/oversized content or an unexpected native adapter extraction, boundary, or result/state-preservation fault | `IntegrationError` or a more specific unsupported-content subtype | Stop affected submission or delivery regardless of policy optionality. |
| Required policy violation | `PolicyViolationError` | Block affected submission or delivery. |
| Required inconclusive judgment | `InconclusiveError` | Block, distinguished from a confirmed violation. |
| Required evaluator/detector runtime error | `EvaluationError` | Block; optional instances become recorded check results. |
| Caller exception or cancellation | Original caller/cancellation exception | Propagate without converting to a guard result. |

An unsupported shape discovered only at runtime is an integration failure; a shape or arrangement identifiable as incompatible during setup is a configuration failure. A required local PII error prevents remote evaluation and affected model submission. Output failures prevent remote output evaluation or delivery. Earlier tool effects, state persistence, and model cost are not rolled back.

## Invariants

- The native snapshot covers supported text forms and limits in [data-model.md](../data-model.md). No text part or nested JSON-compatible string key or value may be silently omitted.
- Local PII checks precede any external evaluation of protected content. Default protection makes no external evaluator call.
- Live and saved-example evaluation share policy definitions and the same decision reducer.
- Request-local state, evidence, results, and credentials never cross into another request.
- Routine records contain only sanitized check, boundary, outcome, settings identity, timing, available metadata, and error category.

The implementation must publish exact typed parameters and supported dependency ranges after pinned-package contract and compatibility tests pass. FR-31–FR-34 and AC-32–AC-34 are mandatory acceptance cases.
