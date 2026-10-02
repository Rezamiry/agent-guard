---
description: "Dependency-ordered implementation tasks for Agent Guard"
---

# Tasks: Agent Guard Python SDK

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/), and [quickstart.md](quickstart.md).

**Organization**: All five user stories are required for v1. Phases follow the spec's P1 then P2 order. A story checkpoint means its controlled behavior can be evaluated independently; the release still requires all stories and all AC-01–AC-34.

**Constitutional execution rule**: Before each behavioral implementation task, add an entry to `docs/testing/oracles.md` with FR/AC IDs, fixture rationale, independently derived expected result, prohibited side effects, and oracle provenance. Write a test that fails for the intended behavior before implementing; an import/setup failure alone is not a valid red test. Keep expectations fixed through green and refactoring. Never generate golden labels or expected metrics from production code.

For red-test tasks whose module does not yet exist, add only the smallest importable stub needed to reach the behavioral assertion, then record that assertion's failure. A missing module or unavailable environment is not red evidence.

## Format: `[ID] [P?] [Story] Description`

- `[P]` means different files with no dependency on another incomplete task in that batch.
- `[USn]` maps to the numbered user story in [spec.md](spec.md).
- Paths are relative to the repository root. Every checkbox remains open until implementation evidence exists.

## Phase 1: Setup

**Purpose**: Establish a separately installable Python package and independent test environment.

- [X] T001 Define Python `>=3.11,<3.13`, Hatchling, typed package metadata, optional `pii`, `jev`, `langchain`, `langgraph`, `microsoft`, and `all` extras, and dev tools in `pyproject.toml`; keep base import free of framework and detector dependencies.
- [X] T002 Create `src/agent_guard/__init__.py` and `src/agent_guard/py.typed` with a minimal importable package that does not load models, frameworks, or credentials.
- [X] T003 Configure deterministic pytest, pytest-asyncio, Ruff, and mypy defaults in `pyproject.toml` and `tests/conftest.py`, with no required network or API key.
- [X] T004 [P] Create `docs/testing/oracles.md` with the required per-behavior record fields and `docs/traceability.md` with FR-01–FR-34 and AC-01–AC-34 placeholders; retain the spec as the authority for expected outcomes.
- [X] T005 Resolve and save `uv.lock` for Python 3.11/3.12 and the selected optional extras; record any dependency changes from [research.md](research.md) in `docs/compatibility.md` before broadening claims.
- [X] T006 Add a packaging smoke check in `tests/contracts/test_package_imports.py` for base import without optional dependencies and independently installable extras; use pinned environments rather than importing all extras into the base package.

**Checkpoint**: A package skeleton and pinned environment exist; deterministic tests can be collected.

---

## Phase 2: Foundational contracts

**Purpose**: Build the shared policy, decision, validation, and failure contracts used by every story.

**Gate**: Finish T001–T006 first. For T007–T019, follow the constitutional red → green sequence and record each behavioral oracle before implementation.

- [X] T007 Define independent decision-table fixtures for required/optional pass, violation, inconclusive, evaluation error, and missing-evidence skip in `docs/testing/oracles.md`; cite FR-12, FR-14–FR-18, and AC-08–AC-10.
- [X] T008 [P] Write intended-failing policy validation tests in `tests/unit/test_policy_models.py` for unique check identities, valid check/boundary combinations, required/optional status, confidence in `[0,1]`, and the required input/output local-PII-only default.
- [X] T009 [P] Write intended-failing reducer tests in `tests/unit/test_decisions.py` for FR-12 and FR-14–FR-18, including no error-as-pass, optional outcomes never overriding required failures, and absent evidence skipped rather than passed.
- [X] T010 [P] Write intended-failing sanitized exception tests in `tests/unit/test_errors.py` for configuration, integration, violation, inconclusive, evaluation, caller, and cancellation categories; include prohibited raw-content/credential sentinels from FR-27 and FR-34.
- [X] T011 Implement immutable `PolicySet`, `CheckPolicy`, `EvaluationContext`, `EvidenceItem`, `CheckResult`, and `BoundaryDecision` in `src/agent_guard/core/models.py`; require unique policy/evidence IDs, scoped evidence association, valid boundaries and outcomes, and absent cost/confidence as unknown rather than zero.
- [X] T012 Implement the pure required/optional decision reducer and independent evidence requirement in `src/agent_guard/core/decision.py`; preserve skipped/not-evaluated outcomes and return the same decision shape for live and saved evaluation.
- [X] T013 Implement sanitized exception classes and stable reason codes in `src/agent_guard/core/errors.py`; integration failures must not be downgraded to optional evaluation outcomes and caller exceptions/cancellation must pass through.
- [X] T014 [P] Write intended-failing native snapshot/limit tests in `tests/unit/test_content.py` for every native text part, textual tool description, nested string key and value in JSON-compatible tool arguments, supported message role, and rejection of opaque/multimodal content without stringification or omission.
- [X] T015 Implement request-local content normalization and validation in `src/agent_guard/core/content.py`; enforce **at most 100,000 Unicode code points without normalization (including tool-argument keys), 128 messages, and 64 identified evidence items**, accept equality only when all limits pass, and reject over-limit or unsupported content before affected disclosure/submission.
- [X] T016 [P] Write intended-failing lifecycle/configuration tests in `tests/unit/test_guard_lifecycle.py` for local preparation, enabled dependency/model/credential presence, disabled-check exemption, invalid settings, post-close use, and zero provider probes.
- [X] T017 Implement sync/async preparation and close lifecycles in `src/agent_guard/core/guard.py`; validate enabled capabilities locally before protected work and keep resources/request state isolated.
- [X] T018 [P] Write intended-failing record-privacy tests in `tests/privacy/test_sanitized_records.py` for raw conversation, detected PII, credentials, arbitrary provider text, unavailable cost, and cross-request leakage.
- [X] T019 Implement sanitized operational record construction in `src/agent_guard/core/records.py` with check, boundary, outcome, policy/settings identity, elapsed time, available confidence/evaluator/usage/cost, and applicable error category; exclude all content and secrets.

**Checkpoint**: Shared models, validator, reducer, lifecycle, and error taxonomy pass controlled tests without external services.

---

## Phase 3: User Story 1 — Protect content before external submission (P1, MVP)

**Goal**: Required local PII prevents disclosure of initial or later assembled input; explicit optional PII is monitoring.

**Independent Test**: With a controlled local detector and a fake model/provider, prohibited PII in initial, history, or retrieved text causes zero affected remote and model calls. Default policy runs only required local PII; optional findings are recorded without content.

### Tests and oracle design

- [X] T020 [US1] Record independently expected safe, PII-blocked, detector-error, later-context-PII, and optional-monitoring cases with forbidden remote/model calls in `docs/testing/oracles.md` for AC-02, AC-03, AC-05, AC-15, AC-16, AC-28, and AC-33.
- [X] T021 [P] [US1] Write intended-failing local detector contract tests in `tests/contracts/test_local_pii.py` for the `english-v1` `en` preset and PERSON, EMAIL_ADDRESS, PHONE_NUMBER (US/CA/GB), CREDIT_CARD, and US_SSN categories; missing model assets fail locally and first use makes no network call.
- [X] T022 [P] [US1] Write intended-failing input orchestration tests in `tests/privacy/test_input_boundary.py` for required finding/error privacy order, assembled history/retrieval additions, new model submissions, optional monitoring, and no default external evaluator call.
- [X] T023 [P] [US1] Write intended-failing boundary-size and changed-snapshot tests in `tests/unit/test_input_snapshots.py`; exact **100,000 Unicode code points without normalization, 128 messages, 64 evidence items** pass when other limits pass, excess rejects before disclosure, and changed content is rechecked before a model call.

### Implementation

- [X] T024 [US1] Implement the offline-only Presidio/spaCy detector loader and curated `english-v1` recognizers in `src/agent_guard/checks/pii.py`; use already installed `en_core_web_lg==3.8.0`, offline TLD extraction, cutoff 0.35, no runtime download, and no advertised categories/languages beyond validated coverage.
- [X] T025 [US1] Implement local input preflight and request-local assembled-content checks in `src/agent_guard/core/input.py`; required PII findings/errors stop remote evaluation and affected model submission, while explicit optional PII records monitoring outcomes without content.
- [X] T026 [US1] Connect `Guard.evaluate_input`/`enforce_input` and async equivalents to the shared reducer in `src/agent_guard/core/guard.py`; run enabled semantic checks only after local privacy preflight, and do not invoke a protected host operation more than once.
- [X] T027 [US1] Add a safe/blocked standalone input example in `examples/core_input.py` and document the default PII dependency and optional-monitoring disclosure consequence in `README.md`.
- [X] T028 [US1] Run the controlled AC-02/03/05/15/16/28 core cases, including changed assembled snapshots; defer full native AC-33 to T057 and record red/green evidence in `docs/testing/oracles.md` and `docs/traceability.md`.

**Checkpoint**: The core input guard is independently usable without a framework or remote evaluator.

---

## Phase 4: User Story 2 — Deliver only answers permitted by policy (P1)

**Goal**: Check final answers locally before external output evaluation and delivery, then apply relevance, groundedness, safety, and custom criteria when enabled.

**Independent Test**: Saved candidate answers with controlled judgments show output PII blocking, relevance/groundedness decisions, missing-evidence skip, unchanged allowed answers, and withheld blocked answers without regeneration.

### Tests and oracle design

- [X] T029 [US2] Record independent final-answer, relevance, groundedness, missing-evidence, content-safety, custom-policy, and prior-side-effect expectations in `docs/testing/oracles.md` for AC-04, AC-06, AC-07, AC-08, AC-11, AC-17, and AC-27.
- [X] T030 [P] [US2] Write intended-failing output privacy tests in `tests/privacy/test_output_boundary.py` for PII in candidate answer or output-evaluation context, zero later remote output evaluation/delivery, and preserved prior cost/tool-side-effect meaning.
- [X] T031 [P] [US2] Write intended-failing semantic check tests in `tests/unit/test_semantic_checks.py` for current-request-in-context relevance, identified-evidence-only groundedness, missing-evidence skip, and required/optional safety and custom outcomes.
- [X] T032 [P] [US2] Write intended-failing provider wire tests in `tests/contracts/test_jev_provider.py` for one choice question, exact pass/violation mapping, requested answer key, finite confidence `[0,1]`, model identity, malformed/unknown response, and no raw-response diagnostic disclosure.

### Implementation

- [X] T033 [US2] Implement versioned semantic rubrics and check-result normalization in `src/agent_guard/checks/semantic.py`; keep governing policy separate from untrusted state, require identified evidence for groundedness, and never treat absent evidence as pass.
- [X] T034 [US2] Implement Jev request/response validation in `src/agent_guard/providers/jev.py`; send only locally inspected content, enforce one named choice question and `pass`/`violation`, require finite confidence in `[0,1]`, preserve unknown usage/cost as unknown, and make no evaluator fallback.
- [X] T035 [US2] Implement local-first final-answer evaluation and enforce operations in `src/agent_guard/core/output.py` and `src/agent_guard/core/guard.py`; inspect candidate plus all external output-evaluation context before remote judgment, withhold blocked answers, and return the original allowed answer.
- [X] T036 [US2] Add controlled-evaluator direct-answer and evidence-backed output examples in `examples/core_output.py`, including missing evidence and a permitted refusal/clarification case; the live Jev path depends on T043.
- [X] T037 [US2] Run controlled-judgment AC-04/06/07/08/11/17/27 core cases and refactor with expectations fixed; record evidence in `docs/testing/oracles.md` and `docs/traceability.md`, with the live provider path completed at T046.

**Checkpoint**: The core output guard decides delivery independently from any framework adapter.

---

## Phase 5: User Story 3 — Configure policies and understand failures (P1)

**Goal**: Expose explicit configuration, consistent required/optional decisions, bounded provider failure behavior, and sanitized diagnostics.

**Independent Test**: Controlled pass, violation, uncertainty, invalid setup, runtime dependency/provider failure, timeout, and throttling cases produce the specified exceptions or optional records without leaking content.

### Tests and oracle design

- [X] T038 [US3] Record independent setup/runtime, confidence-equality, deadline, throttling, cancellation, and optional-monitoring outcomes in `docs/testing/oracles.md` for AC-09, AC-10, AC-14, AC-18, AC-19, AC-29, AC-30, AC-31, and AC-34.
- [X] T039 [P] [US3] Write intended-failing configuration and confidence tests in `tests/unit/test_policy_authoring.py` for valid scopes, the default local-only policy, invalid settings/dependencies/credential presence, and valid semantic confidence equal to or below the configured minimum.
- [X] T040 [P] [US3] Write intended-failing provider deadline/failure tests in `tests/contracts/test_jev_failures.py`; accept only finite **0.1–120.0 seconds** (default 10.0), bound total wait including queue/read/decode, make at most one attempt, and classify 429, timeout, rejection, and unavailability as evaluation errors.
- [X] T041 [P] [US3] Write intended-failing adapter-fault classification tests in `tests/unit/test_failure_taxonomy.py` for setup incompatibility versus unexpected extraction/boundary/state fault; integration failures block even with optional policies, while caller exceptions and cancellation retain their identity.

### Implementation

- [X] T042 [US3] Finish public policy authoring and prepared-capability validation in `src/agent_guard/core/policy.py` and `src/agent_guard/core/guard.py`; enforce check scopes, immutable settings identity, local prerequisite validation, confidence defaults/ranges, and no credential probe.
- [X] T043 [US3] Implement a cancellable one-attempt transport in `src/agent_guard/providers/transport.py`; enforce **512 KiB outbound request and 256 KiB inbound response** limits, monotonic total deadline, no retry/redirect/retry-window wait, and immediate completed-error reporting for sync and async calls.
- [X] T044 [US3] Complete sanitized failure-to-record mapping in `src/agent_guard/core/records.py` and `src/agent_guard/core/errors.py`; keep configuration/integration failures outside optional check results and report unavailable cost as unknown.
- [X] T045 [US3] Add policy authoring and failure-mode examples in `examples/policies.py` and document required/optional semantics and reduced-protection monitoring in `README.md`.
- [X] T046 [US3] Run controlled AC-09/10/14/18/19/29/30/31/34 cases and refactor without weakening fixtures; record evidence in `docs/testing/oracles.md` and `docs/traceability.md`.

**Checkpoint**: Policy authors can configure checks and operators can distinguish all failure classes without content disclosure.

---

## Phase 6: User Story 4 — Adopt native integrations (P2)

**Goal**: Ship LangChain, LangGraph, and Microsoft Agent Framework Python adapters on the exact native boundaries and surfaces in FR-31 and [contracts/integrations.md](contracts/integrations.md).

**Independent Test**: Real framework objects with controlled inference demonstrate safe/blocked direct and retrieval paths, every stated ordinary/async surface, unchanged results/state, changed-payload rechecks, stream rejection, adapter faults, and concurrent isolation.

### Tests and oracle design

- [X] T047 [US4] Record framework-native oracle cases and prohibited side effects in `docs/testing/oracles.md` for AC-01, AC-03, AC-04, AC-11, AC-12, AC-20, AC-21, AC-22, AC-23, AC-32, AC-33, and AC-34; derive expected native state from documented contracts before executing adapters.
- [X] T048 [P] [US4] Write intended-failing LangChain tests with real native messages/agent middleware in `tests/integration/test_langchain.py` for ordinary/async model and final hooks, direct/retrieval answers, added PII, result metadata, late mutation, stream rejection, and no duplicate model call.
- [X] T049 [P] [US4] Write intended-failing LangGraph tests with real graph state/reducers in `tests/integration/test_langgraph.py` for declared model/final branches, exact inspected snapshot, privately assembled prompt rejection, invoke/ainvoke parity, state preservation, and stream rejection.
- [X] T050 [P] [US4] Write intended-failing Microsoft native-async tests in `tests/integration/test_microsoft.py` for context-provider additions before each chat call, final agent result, callback signature from the pinned package, direct/retrieval paths, and unchanged context/result.
- [X] T051 [P] [US4] Write intended-failing shared adapter contract tests in `tests/contracts/test_native_adapters.py` for all supported text parts and nested tool-argument strings, exact-limit/overflow, opaque/multimodal rejection, known late-mutator setup failure, runtime integration error, caller error, and cancellation.

### Implementation

- [X] T052 [US4] Implement shared native extraction and topology validation in `src/agent_guard/integrations/common.py`; preserve roles/part order and JSON structure, recheck changed assembled input, reject known bypassing placement before protected work, and distinguish runtime adapter faults from policy outcomes.
- [X] T053 [US4] Implement LangChain ordinary/async model and final-answer middleware plus non-streaming facade in `src/agent_guard/integrations/langchain.py`; place checks after supported mutations, preserve native result/state, and reject exposed streaming entry.
- [X] T054 [US4] Implement LangGraph declared model/final boundary helpers and non-streaming Runnable facade in `src/agent_guard/integrations/langgraph.py`; guard each exact model-consumed snapshot and every direct/retrieval final path without changing native state reducers.
- [X] T055 [US4] Implement Microsoft native-async chat/agent middleware in `src/agent_guard/integrations/microsoft.py`; inspect post-provider content on each chat call, check completed agent result, and preserve pinned-package callback/result semantics.
- [X] T056 [US4] Add safe/blocked direct and retrieval adoption examples in `examples/langchain_agent.py`, `examples/langgraph_agent.py`, and `examples/microsoft_agent.py`; document observable and unsupported boundaries in `docs/compatibility.md`.
- [X] T057 [US4] Run the real-framework controlled AC-01/03/04/11/12/20/21/22/23/32/33/34 matrix, including concurrent distinct policies/evidence and all claimed execution surfaces; record red/green evidence and compatibility versions in `docs/testing/oracles.md` and `docs/traceability.md`.

**Checkpoint**: Every promised adapter demonstrates safe and blocked native paths without the separate demonstration application.

---

## Phase 7: User Story 5 — Evaluate saved examples (P2)

**Goal**: Evaluate existing answers and compare policies with independent labels, transparent denominators, and content-free reports.

**Independent Test**: A fixed seven-example dataset yields AC-25's independently calculated counts; unlabeled, error, skip, and changed-policy cases do not regenerate answers or invent accuracy.

### Tests and oracle design

- [X] T058 [US5] Record independently calculated AC-25 counts and saved-example decision expectations in `docs/testing/oracles.md` for AC-12, AC-13, AC-24, AC-25, and AC-26; fix labels and denominators before implementation execution.
- [X] T059 [P] [US5] Write intended-failing JSONL import tests in `tests/contracts/test_dataset_jsonl.py` for UTF-8 versioned records, unique example IDs, labels scoped to `(example_id, policy_id, boundary)`, optional evidence, invalid individual-record handling, and context limits.
- [X] T060 [P] [US5] Write intended-failing metric/report tests in `tests/unit/test_metrics.py` for seven total, five classified, one error, one skip, accuracy **3/5**, precision **1/2**, recall **1/2**, false-positive rate **1/3**, classified coverage **5/7**, and undefined denominators as undefined.
- [X] T061 [P] [US5] Write intended-failing live/offline parity and comparison tests in `tests/acceptance/test_offline.py` for identical controlled judgments, unchanged candidate answer, two fixed settings, changed decisions, and no live-policy mutation.
- [X] T062 [P] [US5] Write intended-failing report-privacy tests in `tests/privacy/test_report_export.py` for no raw request/answer/evidence, PII, credentials, content hashes, arbitrary evaluator rationale, or invented zero cost.

### Implementation

- [X] T063 [US5] Implement versioned JSONL saved-example and scoped-label validation in `src/agent_guard/evaluation/dataset.py`; reject invalid global setup before processing and emit sanitized per-line errors without aborting other records.
- [X] T064 [US5] Implement offline evaluation through the shared guard/reducer in `src/agent_guard/evaluation/runner.py`; keep default concurrency one, isolate request contexts, avoid answer regeneration, and record blocks rather than aborting the dataset.
- [X] T065 [US5] Implement per-policy/boundary confusion counts, coverage, aggregate decisions, and undefined-ratio handling in `src/agent_guard/evaluation/metrics.py`; never derive expected fixtures from these functions.
- [X] T066 [US5] Implement sanitized JSON report, CSV aggregate summary, and two-settings comparison in `src/agent_guard/evaluation/report.py`; preserve example/settings identity and exclude all raw content and secrets.
- [X] T067 [US5] Add a fixed-label saved-evaluation example in `examples/offline_evaluation.py` and explain denominators, errors/skips, and possible opt-in provider access in `README.md`.
- [X] T068 [US5] Run controlled AC-12/13/24/25/26 cases with fixed oracle labels and refactor with expectations unchanged; record evidence in `docs/testing/oracles.md` and `docs/traceability.md`.

**Checkpoint**: Evaluation owners can compare policies on saved answers with honest, sanitized metrics.

---

## Phase 8: Polish and release gates

**Purpose**: Validate the complete v1 promise; polish tasks do not excuse missing story acceptance.

- [X] T069 [P] Build a full FR-01–FR-34/AC-01–AC-34 cross-reference with test files, oracle provenance, supported surfaces, and release evidence in `docs/traceability.md`.
- [ ] T070 [P] Freeze independent development/held-out labels, versioned rubrics, source/template-family split, and predeclared per-category quality gates in `evaluations/manifests/v1.md`; keep held-out labels fixed after assessment and report false alarms, misses, classified coverage, uncertainty, overhead, and available cost.
- [X] T071 [P] Prepare the Python/framework/detector/provider version matrix, native boundaries, content limits, and unsupported arrangements in `docs/compatibility.md`; leave measured overhead and untested compatibility claims pending T073–T074.
- [X] T072 [P] Prepare `LICENSE`, `CONTRIBUTING.md`, and `docs/third_party_notices.md` for maintainer license acceptance and dependency/model redistribution review; do not publish before acceptance.
- [X] T073 Run formatting, static/type checks, wheel/sdist metadata/install checks, deterministic tests, and real-framework controlled integration tests on the **oldest and newest version of every advertised dependency range**, then run [quickstart.md](quickstart.md) scenarios; record commands, versions, pass/fail results, and unresolved defects in `docs/release-evidence.md`.
- [ ] T074 Run separately enabled provider smoke and frozen-label quality evaluation after deterministic gates; report elapsed-time and available usage/cost **for every supported check category and integration with sample counts and conditions**, plus outcomes, denominators, and limitations in `docs/release-evidence.md`; a failed predeclared gate blocks release and cannot be fixed by relabeling held-out data.
- [X] T075 Publish tested compatibility ranges and measured overhead in `docs/compatibility.md`, select a semantic version and explain compatibility changes and migration guidance in `RELEASE_NOTES.md`, then review every story and checklist for constitutional compliance, privacy, independent oracles, and unsupported claims in `docs/release-evidence.md`; keep unresolved acceptance cases open.

**Checkpoint**: All advertised checks, integrations, dependency groups, and acceptance cases have evidence; public release awaits maintainer acceptance of license and release review.

---

## Dependencies and execution order

### Phase and story graph

```text
Setup T001–T006
  -> Foundation T007–T019
  -> US1 T020–T028 (input protection; MVP)
  -> US2 T029–T037 (final answers; uses local PII/input foundation)
  -> US3 T038–T046 (policy authoring and provider faults; completes shared checks)
     +-> US4 T047–T057 (native adapters; consumes US1–US3 core) -+
     +-> US5 T058–T068 (saved evaluation; consumes US1–US3 core) -+
  -> Polish T069–T075 (after US4 and US5)
```

US3's policy-validation tests can be designed after Foundation while US1/US2 are underway; its implementation must integrate with the completed core and provider work. US5's dataset/metric tests can be designed after Foundation; its runner depends on US1–US3. US4 depends on all shared live guard behavior. Every story remains independently demonstrable at its checkpoint using controlled dependencies, and all five remain release requirements.

### Within each story

Complete its oracle-design task first. The `[P]` red-test tasks then write different files and can proceed together. Confirm intended behavioral red failures before implementation tasks. Model/validation work precedes orchestration; provider and core work precede adapters and offline runner. Run the story's acceptance task last and document red/green evidence. Tasks touching the same file, including `src/agent_guard/core/guard.py`, `README.md`, and `docs/testing/oracles.md`, are sequential unless coordinated edits are explicitly isolated.

### Parallel examples

| Story | Parallel work after its oracle task | Join before |
| --- | --- | --- |
| US1 | T021 local-detector contract, T022 input privacy, T023 snapshot limits | T024–T026 implementation |
| US2 | T030 output privacy, T031 semantic decisions, T032 provider wire | T033–T035 implementation |
| US3 | T039 policy authoring, T040 provider faults, T041 adapter-fault taxonomy | T042–T044 implementation |
| US4 | T048 LangChain, T049 LangGraph, T050 Microsoft, T051 shared adapter contract | T052–T055 adapters |
| US5 | T059 dataset, T060 metrics, T061 parity/comparison, T062 report privacy | T063–T066 implementation |

## Implementation strategy

1. Finish Setup and Foundation, including independently sourced oracle fixtures and actual behavioral red failures.
2. Deliver US1 as the first independently usable input-protection increment. Its checkpoint is an MVP demonstration, not the v1 release.
3. Complete US2 and US3 to add final-answer protection, authoring, and bounded external judgments.
4. Complete US4 and US5 with real framework contracts and fixed saved-example labels.
5. Pass all Phase 8 release gates; document any limitation before claiming coverage.

Do not mark a task complete because an import failed, a mock alone passed, a generated output was adopted as an oracle, or an unmeasured quality/compatibility claim was assumed true.

---

## Phase 9: Convergence

**Purpose**: Close the remaining gaps between the specified v1 scope and the present code. Appended by `/speckit-converge`; the constitutional red → green and independent-oracle rules still apply to every behavioral item below.

- [X] T076 CRITICAL Reject an asynchronous `assemble`/`submit`/`context` callable passed to `GuardedModelNode` or `GuardedFinalNode` as an identifiable incompatible arrangement at `compile_guarded_graph` time in `src/agent_guard/integrations/langgraph.py`, instead of returning an un-awaited coroutine from the node, per FR-34, AC-34, and Constitution I (contradicts)
- [X] T077 Add the asynchronous LangGraph guarded model and final node surface (async node callables using `aenforce_input`/`aenforce_output`, recognized by `compile_guarded_graph` through the node's async runnable) so the promised "asynchronous native graph use" row is real rather than a sync node run in a thread, per FR-06, FR-31, AC-32 (missing)
- [X] T078 Write concurrency-isolation tests for overlapping requests carrying distinct policies, evidence, and records across the core guard and each native adapter, asserting zero cross-request content/evidence/result mixing, per AC-21, FR-25, SC-005 (missing)
- [X] T079 Exercise a real LangChain tool-calling retrieval journey through `create_guarded_agent` (tool-capable chat model, `AIMessage.tool_calls`, `ToolMessage` result) in `tests/integration/test_langchain.py` and `examples/langchain_agent.py`, asserting the second assembled model request is rechecked and intermediate tool requests are not judged as final answers, per AC-11, AC-32, SC-002 (missing)
- [X] T080 Complete the T073 packaging and dependency-range gates: replace or fix the failing `twine check` metadata validation, provision the `en_core_web_lg` fixture on Python 3.11 so no case is skipped, install each advertised extra independently, and run the oldest and newest version of every claimed dependency range, recording results in `docs/release-evidence.md`, per AC-23, FR-29 (missing)
- [ ] T081 Freeze the independently reviewed development and held-out datasets, their source/template-family split, label provenance, and versioned hash in `evaluations/manifests/v1.md`, replacing every `Pending` freeze-record row before any quality measurement, per AC-26, SC-006, Constitution V (partial)
- [ ] T082 Run the T074 frozen-label quality evaluation and the separately enabled provider smoke, then publish per-category misses, false alarms, coverage, uncertainty, elapsed time, and available usage/cost with sample counts and conditions for every supported check category and integration in `docs/release-evidence.md`, per AC-26, SC-006, SC-007 (missing)
- [X] T083 Run the T057 full native acceptance matrix and add cross-framework parity cases proving identical controlled judgments produce identical per-check outcomes and aggregate decisions across LangChain, LangGraph, Microsoft, and offline evaluation, per AC-12, AC-32, FR-20, SC-003 (missing)
- [X] T084 Assert caller-exception and cancellation identity through the asynchronous adapter paths (`InputGuardMiddleware.awrap_model_call`, `OutputGuardMiddleware.aafter_agent`, `MicrosoftChatGuard.process`, `MicrosoftAgentGuard.process`) in `tests/contracts/test_native_adapters.py`, which today covers only the synchronous LangGraph node, per AC-20, AC-34 (partial)
- [X] T085 Assert that permitted native results preserve metadata and state — LangChain `response_metadata`/`usage_metadata`/message ids and LangGraph state reducer output — rather than only final message text, in the native integration tests, per AC-01, FR-02, SC-002 (partial)
- [X] T086 Move the shared native topology validation and changed-assembled-payload recheck into `src/agent_guard/integrations/common.py` as T052 specifies, and add a LangChain test asserting that a user middleware cannot mutate model-bound content after the guard's innermost placement, per plan: shared native extraction, FR-32, FR-34 (partial)
- [ ] T087 Complete T075: publish tested compatibility ranges and measured overhead in `docs/compatibility.md`, record maintainer license acceptance and the transitive-dependency/model redistribution review, and record the final per-story constitutional compliance review in `docs/release-evidence.md`, per FR-29, SC-007, Constitution "Open Source and Compatibility" (partial)

**Checkpoint**: The promised async LangGraph surface, concurrency and retrieval evidence, and the packaging, quality, and release-review gates are all closed or explicitly recorded as blocked with a named owner.
