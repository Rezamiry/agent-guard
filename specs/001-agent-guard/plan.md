# Implementation Plan: Agent Guard Python SDK

**Branch**: `001-agent-guard` (feature identifier reported by Spec Kit; no working Git repository
is exposed in this workspace) | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-agent-guard/spec.md`; user: “write this sdk in python.”

**Status**: Phase 0 research and Phase 1 design revised for FR-31–FR-34 and AC-32–AC-34.
Implementation and executable validation remain work for the task/implementation phases. This
plan does not create SDK source files or claim runtime framework compatibility.

## Summary

Build a Python SDK with shared policy enforcement for live agents and saved examples. Required
local PII runs by default on input and output; external judgment is explicitly enabled. A typed,
framework-independent core normalizes outcomes, controls privacy ordering, and supplies sanitized
reports. Optional adapters use native LangChain, LangGraph, and Microsoft Agent Framework
boundaries. Presidio runs through offline-only adapters; opt-in Jev uses one bounded HTTP request
per check. Native adapters recheck changed model-bound text, reject unsupported content and known
bypassing arrangements, and distinguish setup, integration, policy, and caller failures. The
active feature spec and its 34 FRs/34 ACs remain the behavioral authority.

## Technical Context

**Language/Version**: Python 3.11 and 3.12; initial package constraint `>=3.11,<3.13`.

**Primary Dependencies**: Pydantic 2; optional Presidio 2.2.364 + spaCy 3.8 + en_core_web_lg 3.8.0;
optional HTTPX 0.28 + AnyIO 4 for Jev; integration contract pins LangChain 1.4.2,
langchain-core 1.6.4, LangGraph 1.2.12, agent-framework-core 1.19.0. Exact transitive resolution
belongs in the implementation lockfile. Pins are source/metadata inspected, not runtime certified.

**Storage**: No service/database. Caller-owned JSONL datasets; sanitized JSON reports/CSV summaries.
No raw-content cache or automatic persistence.

**Testing**: pytest, pytest-asyncio, Hypothesis, controlled transport/detector doubles; real native
framework objects in integration tests. Ruff, mypy, wheel/sdist build and package metadata checks.
Frozen independent labels for separate live/detector quality evaluation.

**Target Platform**: Linux x86-64 first; ordinary and asyncio application flows. Microsoft integration
is native async only; ordinary scripts may run an async main.

**Project Type**: Open source Python SDK; no hosted service, UI, mandatory CLI, or demonstration app.

**Performance Goals**: Publish overhead, quality, and available usage/cost; no universal latency or
accuracy guarantee. Per-judgment deadline default 10 seconds, allowed range 0.1–120 seconds.

**Constraints**: No runtime network in PII; one remote attempt/no retry/no fallback; positive finite
total deadline; configuration validation before disclosure; native result/state preservation;
content-free diagnostics. SDK bounds: 100,000 context characters, 128 messages, 64 evidence items,
512 KiB request body, 256 KiB response body. Supported native content includes every text part in
covered messages, textual evidence/tool descriptions, and all string leaves in JSON-compatible
tool arguments; preserve structure and reject opaque or multimodal model-bound content. Equality
with a limit is accepted only when all other limits pass. A known bypassing late mutator fails
setup; an unexpected adapter extraction or result/state fault fails as an integration error
regardless of optional check status.

**Scale/Scope**: Six check types, three integrations, two supported Python versions, sync/async core,
iterable offline evaluation with default concurrency one. Request-local mutable state; immutable
policies; no database or global judgment cache. Multi-request isolation is required regardless of
caller concurrency. All five user stories ship in v1.

**Environment observed**: System `python3` is 3.8.10 and uv is available. Future validation must
provision the declared Python versions; no dependencies were installed during this planning run.

## Constitution Check

*GATE: assessed before research and re-evaluated after design. “Pass” describes design compliance,
not successful implementation or live evaluation.*

| Constitutional gate | Before research | After design and evidence |
| --- | --- | --- |
| I. Independent library/native integration | Pass: core plus optional adapters planned | Pass: contracts define each native boundary and execution surface, unchanged result/state, and optional framework dependencies. |
| II. Privacy before external processing | Pass: local stage required by spec | Pass: contracts inspect every supported text part and changed assembled payload before disclosure; opaque content and known bypassing arrangements fail explicitly. |
| III. Shared explicit enforcement | Pass: spec decision table adopted | Pass: one reducer and distinct configuration, integration, evaluation, caller, and cancellation failures; optional policy cannot mask adapter failure. |
| IV. Independent oracles and TDD | Pass: preserved from constitution | Pass: traceable acceptance matrix and oracle -> red -> green workflow; no observed-output goldens. |
| V. Honest evaluation/observability | Pass: separate behavioral/quality evidence | Pass: scoped labels, denominator rules, frozen dataset gates, null cost and safe reason codes. |
| Open source/compatibility | Pass: independently installable SDK | Pass: explicit extras/pins; license/notice and tested-range release gates; no unsupported compatibility claim. |
| Workflow/governance | Pass: spec and checklists reviewed | Pass: 33/33 security, 27/27 integration, and 16/16 spec-quality checklist items reviewed; no exceptions or omitted integrations. |

License ratification, package compatibility tests, and quality measurements are future release gates.
No failed measurement is being treated as a pass. No constitutional exception is requested.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-guard/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── python-sdk.md
│   ├── provider.md
│   ├── integrations.md
│   └── evaluation.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── integrations.md
└── tasks.md                 # generated next by speckit-tasks, not by this command
```

### Source Code (repository root)

Planned implementation layout; these files do not exist yet:

```text
pyproject.toml
uv.lock
LICENSE
README.md
CONTRIBUTING.md
src/agent_guard/
├── __init__.py
├── py.typed
├── core/                   # policies, contexts, results, pure reducer, errors, orchestration
├── checks/                 # local PII adapter, versioned semantic rubrics
├── providers/              # Jev wire validation and bounded async transport/sync portal
├── integrations/           # langchain.py, langgraph.py, microsoft.py
└── evaluation/             # JSONL reader, report, comparison, metrics
examples/                   # safe/block, direct/retrieval per integration
tests/                      # directory layout below
```

Test directories: `tests/unit`, `tests/contracts`, `tests/integration`, `tests/acceptance`,
`tests/privacy`, `tests/quality`. Supporting artifacts: `docs/testing/oracles.md`,
`docs/traceability.md`, `docs/compatibility.md`, `evaluations/manifests/`, and decision records.

**Structure Decision**: One installable package with optional capability extras (`pii`, `jev`,
`langchain`, `langgraph`, `microsoft`, `all`) and a dev dependency group. The base import is light;
default protective use requires `[pii]` and its provisioned model. CI tests minimal imports and
individual extras as well as the full installation. Model assets are installed explicitly.

## Execution Architecture

1. Prepare immutable configuration and all enabled local dependencies. Check credential presence
   only when remote checks are enabled; do not make authentication probes.
2. Extract a request-local snapshot using native contracts and explicit host selectors. Preserve
   roles, current turn, evidence identity, ordered native text parts, and model-bound textual tool
descriptions and nested string argument keys and values. The snapshot must be the content consumed at
   the model boundary; a changed snapshot after an earlier check is checked again.
3. Validate shape/size and run local PII over all fields intended for external disclosure. Count
   supported text as Unicode code points without normalization, including JSON argument keys;
   accept the exact 100,000-code-point, 128-message, and 64-evidence-item limits only when all limits pass;
   reject overflow, multimodal parts, and opaque model-bound objects without flattening. A required
   violation/error ends this boundary without remote checks; later checks are skipped with reason.
4. Run enabled semantic checks in stable policy order, sequentially after local inspection. Stop
   on a required failure. Optional results never reverse required failures. Per-check remote
   payload preparation includes a local privacy preflight over any additional text it introduces.
5. Call the protected native handler once when input allows. Do not catch caller exceptions inside
   the guard evaluation handler. Each subsequent model submission gets its own assembled-input check.
6. At a declared final boundary, inspect output/context locally before remote output judgments.
   Missing evidence skips groundedness; an independent evidence requirement can still block.
7. Emit sanitized results. Live `enforce` raises on block; `evaluate` and offline mode return the
   same decision in a report. Adapters return unchanged native results when permitted.

An identifiable incompatible arrangement, including a known later mutator that bypasses the
last observable guard, fails configuration before protected work. Unexpected adapter extraction,
boundary-identification, or result/state-preservation faults are integration failures and stop
affected submission or delivery even when policy checks are optional. Caller exceptions and
cancellation propagate; neither is converted into a policy result. Documentation identifies
unobservable arbitrary host changes rather than claiming protection over them.

Default detector calls in async mode use a bounded worker and adapter-owned lock/instance isolation;
cancelled awaiting requests never proceed to remote processing. Uninterruptible local work may
finish in its worker, but cannot submit remote requests or mutate another request's context.
Remote mode uses cancellable async I/O in both sync and async public surfaces. Guard resources
are not shared across preparation modes, processes, or event loops.

## Phase 0 — Research Decisions

[research.md](research.md) resolves package baseline, local PII preset/provisioning, provider schema,
deadline strategy, native hooks, data/report contracts, and measured release gates. Its R5–R6
decisions now cover FR-31–FR-34's content scope, limits, late mutations, and integration faults.
Research used primary documentation, official SDK sources, and published package interfaces.
Dependencies are selected rather than assumed installed. No unresolved product clarification
remains; pinned-package contract execution and installation remain implementation gates.

## Phase 1 — Design Artifacts

- [data-model.md](data-model.md): fields, identity, validation, privacy boundaries, state transitions.
- [Python SDK contract](contracts/python-sdk.md): lifecycle, policy builders, evaluate/enforce APIs,
  extension protocols, exceptions, sync/async behavior.
- [Provider contract](contracts/provider.md): exact Jev envelope, strict outcome mapping, total
  deadlines, bounded bodies, cancellation, one-attempt rule.
- [Integration contract](contracts/integrations.md): native hooks, order/topology, extraction,
  supported execution surfaces/content, changed-payload rechecks, unsupported configurations,
  integration faults, and stream rejection.
- [Evaluation contract](contracts/evaluation.md): versioned JSONL, scoped labels, safe exports,
  denominators, comparison, quality manifests.
- [quickstart.md](quickstart.md): implementation-ready setup and validation commands with expected
  outcomes, clearly labeled as future runnable scenarios.

The design artifacts above now exist. They are proposed contracts, not evidence that framework
hooks, package extras, examples, or provider calls run in this workspace. Acceptance evidence must
execute against pinned dependencies and independently authored expected outcomes.

## Implementation Sequencing and Acceptance Ownership

Every work package first records independent expectations and intended red failures, then implements
and refactors. Planning creates no production code or test suite. `speckit-tasks` will expand these
packages into dependency-ordered tasks without omitting required acceptance IDs.

| Work package | Dependencies | Acceptance ownership |
| --- | --- | --- |
| W0 Packaging, pinned environments, oracle register, fixtures | None | AC-23; settings/source provenance for all ACs |
| W1 Validated contracts, pure reducer, lifecycle, exceptions | W0 | AC-08, AC-09, AC-10, AC-14, AC-18, AC-29, AC-30, AC-34 |
| W2 Privacy-first orchestration, native content validation, and offline detector | W1 | AC-02, AC-03, AC-04, AC-05, AC-15, AC-16, AC-19, AC-28, AC-33, AC-34 |
| W3 Jev wire/transport/deadline and semantic rubrics | W1–W2 | AC-06, AC-07, AC-09, AC-17, AC-18, AC-27, AC-30, AC-31 |
| W4 All three native integrations and nonstream facades | W1–W3 | AC-01, AC-03, AC-04, AC-11, AC-12, AC-20, AC-21, AC-22, AC-23, AC-32, AC-33, AC-34 |
| W5 Saved evaluation, comparisons, metrics, safe exports | W1–W3 | AC-12, AC-13, AC-19, AC-24, AC-25 |
| W6 Quality, compatibility, privacy, packaging, docs/release evidence | W4–W5 | AC-26 and full AC-01–AC-34 regression matrix |

Deterministic release evidence must demonstrate both native answer paths, every supported execution
style, prohibited side effects, and cross-framework/offline equivalence. Targeted fault checks cover
required/optional reversal, error-as-pass, remote-before-PII, direct-answer bypass, and missing-evidence
pass. FR-31–FR-34 add per-framework boundary, changed-payload, exact-limit/overflow, unsupported
content, and configuration-versus-integration fault cases. Every claimed framework version and
surface must run with real native objects and controlled inference; Microsoft callback signatures
must be checked against its pinned installed package because current official documents differ.
Never derive golden outputs, expected labels, or metric expectations by running production code.

## Complexity Tracking

No constitutional violations. The persistent sync portal and offline detector adapters are the two
necessary complexities: plain blocking HTTP does not provide cancellable total deadlines, and default
PII library initialization can perform network access. No extra service or storage layer is introduced.
