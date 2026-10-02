# Independent Oracles

For each behavioral task, record the requirement IDs, fixture rationale, expected result,
prohibited side effects, independent authority, intended red failure, green result, and reviewer.
Implementation output must never become its own expected value.

## Input boundary stops after required semantic failure

- **Requirements**: FR-08–FR-10, FR-15–FR-18; AC-05, AC-09, AC-16.
- **Authority**: `spec.md` requires local PII before external judgment and required failures to stop the affected boundary; `plan.md` execution step 4 says to run semantic checks in policy order and stop on a required failure.
- **Fixture rationale**: A safe assembled request has required input PII, followed by a required prompt-injection check returning a confident violation and a later custom input check. A second case makes the prompt-injection check optional.
- **Expected outcomes**: In the required case, the first semantic violation blocks and the later check is recorded as skipped without invoking its evaluator. In the optional case, both semantic checks run and the optional violation alone permits the boundary. Ordinary and async operations make the same decisions.
- **Prohibited side effects**: No later remote judgment or protected model submission after the required failure; no optional violation can reverse a required failure.
- **Oracle provenance**: Derived from the specified decision table and ordered execution rule before the new test was run.
- **Red evidence**: On 2026-09-28, the ordinary and async assertions in `tests/privacy/test_input_boundary.py` failed because both invoked the later evaluator (`['injection', 'later']` instead of `['injection']`).
- **Green evidence**: The same assertions and the adjacent input/core semantic tests passed (11 tests) after ordered early-stop orchestration was added.

## US1 controlled input scenarios

- **Requirements**: FR-03, FR-08–FR-10, FR-15–FR-19; AC-02, AC-03, AC-05, AC-15, AC-16, AC-28, AC-33.
- **Authority**: The input privacy order, default policy, optional-monitoring rule, and assembled-context requirements in `spec.md`; the prohibited remote/model-call outcomes are independent of the current guard implementation.
- **Fixture rationale**: Use a detector that recognizes the synthetic email `secret@example.com`; an evaluator and model handler count calls. Test (1) a safe current request, (2) the email in the initial request, (3) the email added in a tool/history or identified retrieved evidence item after an earlier safe check, (4) a detector that raises, and (5) explicit optional input PII with the email. Repeat assembled snapshots before each model handoff.
- **Expected outcomes**: The safe request permits one model handoff under the default local-only policy with no semantic evaluator call. Required PII in initial or newly assembled text blocks before the affected model and evaluator calls. A required detector error blocks as evaluation error with a sanitized reason and zero later calls. Optional PII records a violation and permits a model handoff when other required checks pass; this is monitoring with reduced protection. A changed snapshot receives a fresh check, including all identified pre-generation evidence even without a generation ID.
- **Prohibited side effects**: No affected model submission or remote semantic judgment after a required local finding/error; no reuse of an earlier safe verdict for changed text; no raw email in decisions, records, or exceptions; no implicit external evaluator under the default policy.
- **Oracle provenance**: Manually derived from the cited spec acceptance cases and privacy-first execution order before this scenario matrix is executed.
- **Red evidence**: The ordered input semantic subcase failed behaviorally before the orchestration change, as recorded above. The earlier core input boundary tests also have behavioral red evidence in their own section. The full AC-33 native matrix remains pending T057.
- **Green evidence**: A focused 16-test controlled core/detector run on 2026-09-28 covered AC-02/03/05/15/16/28, including new assembled snapshots and explicit optional PII findings/errors. The native AC-33 matrix remains pending T057.

## Request-local sanitized records

- **Requirements**: FR-24, FR-27, FR-34; AC-19, AC-26, AC-34.
- **Authority**: The routine-record field allowlist and content exclusion in `spec.md` and the constitution.
- **Fixture rationale**: One request carries a synthetic email, credential, and arbitrary provider exception text; a later clean request uses the same guard. Construct records from both decisions and inspect their serialized form and unknown cost.
- **Expected outcomes**: The first record contains only safe check/boundary/outcome/policy/reason/timing/available metadata; unavailable cost is null. Neither record contains any request, evidence, PII value, credential, or provider exception text. The second record has no state or metadata from the first.
- **Prohibited side effects**: No cross-request field carryover and no invented zero cost.
- **Oracle provenance**: Derived from the explicit allowlist and request-isolation rule before executing this expanded record test.
- **Red evidence**: The earlier metadata-validation assertion failed behaviorally before the `CheckResult`/record validation change, as recorded below. The expanded test initially failed on a fixture substring collision (`second` in `elapsed_seconds`); the request IDs were made unique without changing the expected privacy behavior.
- **Green evidence**: Four sanitized-record tests passed on 2026-09-28, including arbitrary provider text, unknown cost, and cross-request isolation.

## Input snapshot limits and fresh inspection

- **Requirements**: FR-08–FR-10, FR-33; AC-03, AC-14, AC-33–AC-34.
- **Authority**: The spec's inclusive limits of 100,000 Unicode code points without normalization, 128 messages, and 64 identified evidence items, plus the requirement to recheck every changed model-bound snapshot.
- **Fixture rationale**: Use exactly and one beyond each bound, including a combining mark that counts as its own code point. Reuse a request identity with a later tool message containing synthetic PII.
- **Expected outcomes**: Equality at each bound permits inspection when all other limits pass. One over any bound raises a sanitized integration failure before detector/evaluator/model access. A changed snapshot with the same request ID is inspected afresh and blocks on PII.
- **Prohibited side effects**: No truncation, Unicode normalization, stale safe decision reuse, model submission, or remote judgment for over-limit or PII-contaminated snapshots.
- **Oracle provenance**: Manually calculated from the numerical bounds and fresh-snapshot rule before the test run.
- **Red evidence**: The earlier foundational content-limit test has behavioral red evidence; these expanded equality/overflow fixtures passed against existing code and therefore do not establish a new red cycle for T023.
- **Green evidence**: All three `tests/unit/test_input_snapshots.py` cases passed on 2026-09-28. The dedicated changed-snapshot case is covered by `tests/privacy/test_input_boundary.py`.

## Explicit request field remains inside privacy preflight

- **Requirements**: FR-08–FR-10, FR-27, FR-30; AC-03–AC-04, AC-16, AC-34.
- **Authority**: The spec requires local inspection of every field disclosed to an external evaluator; the Jev contract includes `current_request` in `state` even when the host messages also carry a request.
- **Fixture rationale**: Mark `current_request_in_messages=True`, supply safe native messages, and put a synthetic email only in the separate `current_request` field. Enable one semantic check and count evaluator calls at input and output.
- **Expected outcomes**: Required local PII blocks both boundaries and the external evaluator receives zero calls. The hint that a request appears in messages does not exempt the separately serialized field from inspection.
- **Prohibited side effects**: No semantic provider call with the synthetic email, no candidate delivery, and no reliance on a caller hint to omit a disclosed field.
- **Oracle provenance**: Derived from the serialized Jev state contract and the privacy-before-disclosure rule before running the new regression test.
- **Red evidence**: On 2026-09-28, both input and output tests failed behaviorally: the input semantic evaluator was called, and output was allowed when the explicit request alone contained PII.
- **Green evidence**: All eight focused input/output privacy tests passed after the guard always inspected the separately serialized request field.

## US2 final-answer decision scenarios

- **Requirements**: FR-04, FR-08–FR-12, FR-15–FR-18; AC-04, AC-06–AC-08, AC-11, AC-17, AC-27.
- **Authority**: The output-boundary acceptance cases, evidence-association rule, and required/optional decision table in `spec.md`.
- **Fixture rationale**: Use a fixed safe candidate, a candidate with synthetic PII, identified matching and unrelated evidence, a relevance answer that misses the current request, controlled safety/custom pass and violation judgments, and a refusal/clarification that is relevant without fabricated evidence. Count final delivery and remote judgment calls; separately count a prior simulated model/tool effect.
- **Expected outcomes**: Candidate or output-context PII blocks before remote output judgment and delivery. Required relevance, safety, or custom violation blocks; optional violation records and permits if required checks pass. Groundedness uses only identified evidence associated with the candidate generation; absence yields skipped, and the separate evidence-required setting blocks when enabled. A relevant refusal/clarification may pass. Allowed output is the identical candidate string. Prior model cost/tool effects remain counted after an output block.
- **Prohibited side effects**: No output delivery or remote judgment after required local PII finding/error, no answer regeneration or rewriting, no unrelated evidence sent for grounding, and no claim that the guard reverses earlier effects.
- **Oracle provenance**: Derived from the listed acceptance cases and the output/evidence contracts before the full US2 matrix run.
- **Red evidence**: The explicit request field and independent-evidence early-stop cases have separate behavioral red evidence above; the original groundedness-association case has red evidence in its own section.
- **Green evidence**: A focused 31-test controlled core/provider run on 2026-09-28 covered AC-04/06/07/08/11/17/27 with fixed evaluator judgments, safe/blocked direct and retrieval candidates, and untrusted evidence retained as state. Live provider execution remains T046 and native paths remain T057.

## Independent evidence requirement stops later output judgment

- **Requirements**: FR-12, FR-17–FR-18; AC-08.
- **Authority**: The spec's independent evidence requirement and the plan's stop-on-required-failure rule.
- **Fixture rationale**: A safe candidate has no identified generation evidence; groundedness precedes a custom output judgment, and `evidence_required=True`.
- **Expected outcomes**: Groundedness is skipped, the boundary blocks for absent required evidence, and the later external custom judgment is skipped without an evaluator call.
- **Prohibited side effects**: No fabricated groundedness pass and no unnecessary external judgment after the boundary is already blocked by missing required evidence.
- **Oracle provenance**: Derived from the independent evidence rule and ordered evaluation plan before running the regression.
- **Red evidence**: On 2026-09-28 the ordinary test found the later custom judgment was recorded as pass despite absent required evidence; the expected skipped assertion failed.
- **Green evidence**: Ordinary and async cases passed with all six semantic tests after ordered early-stop logic accounted for the independent evidence requirement.

## Shared versioned semantic rubric and normalization

- **Requirements**: FR-09, FR-11–FR-12, FR-17, FR-30; AC-06–AC-08, AC-17–AC-18.
- **Authority**: The provider contract's one-choice `pass`/`violation` rubric and the spec's fixed confidence rule. The v1 rubric text is fixed in this implementation record before its shared module is exercised.
- **Fixture rationale**: A relevance check asks whether the final answer addresses the current request in context; groundedness asks whether identified evidence supports the answer. A valid `0.80` pass and `0.79` pass are normalized with the default minimum. A mismatched check identity is invalid.
- **Expected outcomes**: Rubric version is `v1`; relevance and groundedness criteria differ and each has explicit pass/violation text. Confidence equal to 0.80 stays pass; 0.79 is inconclusive; a mismatched result is rejected. The Jev request keeps governing criteria in instructions and untrusted conversation/evidence in state.
- **Prohibited side effects**: No absent-evidence pass, no untrusted state promoted into governing instructions, and no new provider call during normalization.
- **Oracle provenance**: Derived from the cited spec and provider contract before testing the new shared module.
- **Red evidence**: On 2026-09-28, three assertions failed behaviorally against an importable shared-module stub: relevance rubric text, below-minimum confidence, and mismatched result rejection.
- **Green evidence**: All 20 focused semantic/provider tests passed after the guard and Jev provider used the shared v1 rubric/normalizer. Ruff and mypy passed for 23 source files.

## US3 configuration and provider-failure matrix

- **Requirements**: FR-14–FR-19, FR-24, FR-27, FR-30, FR-34; AC-09–AC-10, AC-14, AC-18–AC-19, AC-29–AC-31, AC-34.
- **Authority**: The required/optional decision table, setup/runtime failure taxonomy, 0.1–120.0-second total deadline, one-attempt transport rule, and sanitized record contract in `spec.md`, `contracts/provider.md`, and `contracts/python-sdk.md`.
- **Fixture rationale**: Apply fixed pass/violation/inconclusive/error outcomes at confidence exactly 0.80 and below it; configure missing detector/evaluator/credential and disabled checks; use a controlled transport for 429, rejection, timeout, unavailability, malformed response, and cancellation. Count attempts and elapsed time. Inject arbitrary secret-bearing exception text from a provider and an adapter.
- **Expected outcomes**: Invalid setup fails before protected work with `ConfigurationError` and no credential probe. Equality with the confidence minimum accepts the valid outcome; below it is inconclusive. Required violation/inconclusive/evaluation error blocks with distinct reasons; optional runtime outcomes record and permit only if remaining required checks permit. 429/rejection/timeout/unavailability use at most one provider attempt, never wait for a retry window, and completed errors surface promptly. Integration faults stop regardless of optionality; caller exceptions and cancellation retain identity. Records contain safe reason/category and unknown cost remains null.
- **Prohibited side effects**: No remote request during setup, no retries/fallback, no content or credentials in routine diagnostics, no optional pass overriding a required failure, and no swallowing cancellation/caller errors.
- **Oracle provenance**: Manually derived from the cited contracts and decision table before the full US3 fault matrix run.
- **Red evidence**: Policy identity, adapter fault, portal queue, and decode deadline behavioral failures are recorded in their dedicated sections. Earlier confidence, record, and provider-wire cases have separate red evidence.
- **Green evidence**: A focused 67-test controlled US3 run on 2026-09-28 covered AC-09/10/14/18/19/29/30/31/34 across policy, reducer, Jev wire/transport, sanitized records, and adapter-fault cases. It used approved unsandboxed execution for worker-thread tests. No live provider smoke was run.

## Provider deadline includes response decoding

- **Requirements**: FR-30, FR-34; AC-31.
- **Authority**: The provider contract states that the finite total deadline includes queue, read, and decode time, with one attempt and no retry.
- **Fixture rationale**: A controlled 200 response arrives promptly, but JSON decoding is deliberately delayed beyond a 0.1-second deadline. Count outbound calls and wall time from `apost` to error.
- **Expected outcomes**: The operation raises sanitized `provider_timeout` close to the configured deadline rather than waiting for the delayed decoder to finish; exactly one request was attempted.
- **Prohibited side effects**: No retry, fallback, raw response in the exception, or delayed successful result after the deadline.
- **Oracle provenance**: Derived from the explicit total-deadline contract before running this transport regression.
- **Red evidence**: On 2026-09-28, delayed JSON decoding exceeded the 0.1-second deadline in a behavioral assertion. A second regression showed synchronous portal scheduling waited about 0.3 seconds before the request timeout could take effect.
- **Green evidence**: Bounded thread decoding and a separately bounded portal submission made all 20 focused transport/Jev cases pass outside the sandbox, followed by the full 154-test suite, Ruff, and mypy. The sandbox blocks worker threads, so thread-dependent tests were run with approved unsandboxed execution.

## Adapter extraction faults versus protected caller faults

- **Requirements**: FR-31, FR-34; AC-20, AC-22, AC-34.
- **Authority**: The integration and Python SDK contracts classify unexpected adapter extraction/boundary faults as integration failures, known incompatible topology as configuration failure, and caller exceptions/cancellation as their original types.
- **Fixture rationale**: A LangGraph model-node assembler raises an unexpected runtime exception before submission; a separate guarded node assembles a safe context but its protected submit callback raises a caller exception or cancellation. Use an optional PII policy to show adapter errors cannot become monitoring results.
- **Expected outcomes**: The assembler fault becomes a sanitized `IntegrationError` and the submit callback is not invoked. The protected caller exception and cancellation propagate unchanged after input permits. A known graph topology bypass is a configuration error before execution.
- **Prohibited side effects**: No affected model call after extraction fault, no optional downgrade of an integration failure, no raw host exception text, and no conversion of caller/cancellation failures into check results.
- **Oracle provenance**: Derived from the stated exception ownership in the integration and SDK contracts before the regression tests run.
- **Red evidence**: On 2026-09-28, the LangGraph assembler-fault test failed because a raw `RuntimeError` escaped from the selector instead of a sanitized integration error.
- **Green evidence**: All nine focused failure-taxonomy and native LangGraph tests passed after selector faults were classified, while protected submit callback exceptions remained unchanged.

## Non-secret policy settings identity

- **Requirements**: FR-07, FR-19, FR-23–FR-24, FR-27; AC-14, AC-19, AC-24, AC-29.
- **Authority**: The data model requires a stable settings fingerprint derived from non-secret configuration; the spec requires policy comparisons and content-free diagnostics.
- **Fixture rationale**: Construct two identical immutable policies, then change a check's required flag, confidence minimum, ordered check list, or declared custom-criterion revision. Keep a synthetic email only in custom criteria to test diagnostic exclusion.
- **Expected outcomes**: Identical declared settings yield the same settings ID; each non-secret setting/revision change yields a different ID. The ID is safe to include in records and reports, while criteria text and credentials are absent. Disabled checks remain exempt from prerequisite validation, and enabled checks still validate locally without a credential probe.
- **Prohibited side effects**: No raw criterion, credential, request, answer, evidence, or content hash in the ID or diagnostics; no remote setup call.
- **Oracle provenance**: Derived from the data model and privacy/traceability contract before the policy-identity tests run. Authors must advance an explicit non-secret criterion revision when changing sensitive criterion text.
- **Red evidence**: On 2026-09-28, the importable policy stub gave the same ID for changed required status, and an unsafe criterion revision was accepted. A separate report assertion failed because the settings ID was absent.
- **Green evidence**: Five policy-authoring cases and the saved-report privacy/comparison cases passed after non-secret settings identity and report propagation were implemented. The full 165-test suite, Ruff, and mypy passed outside the sandbox where thread-dependent provider tests can run.

## US4 framework-native boundary matrix

- **Requirements**: FR-01–FR-06, FR-08–FR-12, FR-25, FR-31–FR-34; AC-01, AC-03–AC-04, AC-11–AC-12, AC-20–AC-23, AC-32–AC-34.
- **Authority**: `contracts/integrations.md`, the spec's Native Integration Coverage section, and the pinned framework object/callback contracts listed there. Expected native result identity, message order, and graph state are derived from those framework contracts before the new matrix runs.
- **Fixture rationale**: For each framework, use a real native message/state object with a controlled fake model. Exercise (1) a safe direct answer, (2) a safe answer after identified retrieval, (3) PII in initial or provider-added history/evidence, (4) PII in a final candidate, (5) a second model submission after changed content, (6) multipart text and nested tool-argument strings, (7) exact-limit and overflow/opaque content, and (8) a known late mutator versus an unexpected runtime selector/extraction fault. Run ordinary and async where promised, Microsoft native async, and concurrent distinct policy/evidence cases.
- **Expected outcomes**: Every model-bound snapshot is checked immediately before its one protected call. Initial or later PII causes zero affected model/evaluator calls. Direct and retrieval final answers each run one final check; intermediate tool requests are not final answers. Allowed LangChain responses/messages, LangGraph state/reducers, and Microsoft `AgentResponse`/`ChatResponse` objects retain native identity and metadata. A blocked final answer is withheld without reversing prior model/tool effects. Stream entry fails before work. Known bypassing topology fails setup; runtime adapter faults are integration errors even under optional policies. Caller exceptions and cancellation propagate.
- **Native boundary mapping**:

  | Framework | Input observation | Final observation | Surface |
  | --- | --- | --- | --- |
  | LangChain | Native `ModelRequest` wrapper after supported mutations | `after_agent` on completed assistant answer | `invoke`, `ainvoke`; stream entries reject |
  | LangGraph | Declared guarded model node receives the exact assembled `EvaluationContext` consumed by its submit callback | Declared final node on every end path | `invoke`, `ainvoke`; stream entries reject |
  | Microsoft Agent Framework Python | Chat middleware after context providers, before each chat client call | Agent middleware on completed `AgentResponse` | Native async `Agent.run`; stream entry rejects |

- **Prohibited side effects**: No duplicate model call, dropped text part, flattened JSON argument, false pass for absent evidence, changed state/message ID, cross-request leakage, evaluator call after local block, or raw content in diagnostics.
- **Oracle provenance**: Transcribed and manually derived from the integration contract and native framework object semantics before extending the real-object matrix; it is independent of adapter output.
- **Red evidence**: Pending new full native matrix; the LangGraph selector-fault regression has separate red evidence above.
- **Green evidence**: The 2026-09-28 controlled native subset passed in the 176-test suite: real LangChain and LangGraph ordinary/async calls, Microsoft native async calls, post-provider retrieval text, exact 100,000-code-point LangChain input, multipart text, nested JSON tool arguments, opaque-content rejection, and sanitized adapter extraction failure. The full matrix, including privately assembled LangGraph prompts, late mutators, concurrent distinct policies, and dependency-range endpoints, remains pending T057.

## Decision table for required and optional checks

- **Requirements**: FR-12, FR-14–FR-18; AC-08–AC-10.
- **Authority**: The required/optional outcome table and absent-evidence rule in `spec.md`.
- **Fixture rationale**: Apply one check outcome at a time, then combine a required failure with an optional pass. Vary the independent evidence requirement with a groundedness skip.
- **Expected outcomes**:

  | Outcome | Required | Optional |
  | --- | --- | --- |
  | Pass | Permit if all other required checks permit | Record and continue |
  | Violation | Block as violation | Record and continue |
  | Inconclusive | Block as inconclusive | Record and continue |
  | Evaluation error | Block as evaluation failure | Record and continue |
  | Groundedness skipped for absent evidence | Permit only if evidence is not separately required | Record and continue; separate evidence requirement still blocks |

- **Prohibited side effects**: No optional outcome may override a required block; a skipped or unrun check cannot be recorded as pass; no provider or model call occurs in the reducer.
- **Oracle provenance**: Transcribed from the spec decision table before this task's test run; the table is independent of reducer output.
- **Red evidence**: Foundational reducer assertions failed behaviorally before the reducer implementation on 2026-09-28, as recorded below.
- **Green evidence**: The decision tests passed in the local deterministic suite on 2026-09-28.

## Result model scope validation

- **Requirements**: FR-14–FR-18, FR-27; AC-09–AC-10.
- **Authority**: The spec's finite set of boundaries and outcomes, and the immutable result contract.
- **Fixture rationale**: Unknown boundary, unknown outcome, non-Boolean required flag, and malformed decision collection.
- **Expected outcomes**: Construction rejects all malformed values before the reducer can mistake an unknown outcome for permission.
- **Prohibited side effects**: No policy pass, content disclosure, or external call from malformed result state.
- **Oracle provenance**: Derived from the enumerated contract before the validation change.
- **Red evidence**: `test_result_and_decision_reject_unrecognized_status_or_scope` failed on its first behavioral assertion on 2026-09-28.
- **Green evidence**: The new assertion passed in the 84-test local deterministic suite on 2026-09-28; Ruff and mypy were rerun after validation.

## Disabled check prerequisites

- **Requirements**: FR-08, FR-19; AC-14–AC-15, AC-29.
- **Authority**: The spec requires prerequisites for enabled checks and explicitly exempts disabled checks; the default remains required local PII on both boundaries.
- **Fixture rationale**: Explicitly disable both PII checks and prepare without a detector; separately disable an extra relevance check while required PII remains active and prepare without an evaluator.
- **Expected outcomes**: Both preparations succeed without a detector or evaluator probe for their disabled capabilities; active default PII still requires a detector; enabled relevance still requires an evaluator.
- **Prohibited side effects**: No disabled detector or evaluator preparation, provider probe, model call, or silent disabling of a check marked enabled.
- **Oracle provenance**: Derived from FR-19 and the default-policy rule before implementation.
- **Red evidence**: `test_disabled_checks_do_not_require_or_prepare_dependencies` failed behaviorally because a disabled detector was prepared on 2026-09-28.
- **Green evidence**: The lifecycle test and static checks passed after filtering enabled resources and checks; full-suite validation followed.

## Foundation: policy, decisions, and content

- **Requirements**: FR-07, FR-08, FR-12, FR-14–FR-18, FR-33; AC-08–AC-10, AC-28, AC-34.
- **Authority**: The spec's default-policy sentence, required/optional decision table, evidence-absence rule, and the 2026-09-27 content-scope amendment.
- **Fixture rationale**: Two default PII boundary policies; one required evaluation error followed by an optional pass; a groundedness skip with and without an independent evidence requirement; a nested JSON argument whose key contains a synthetic email; 100,000 versus 100,001 Unicode code points using combining marks; input relevance as an invalid boundary.
- **Expected outcomes**: Two required default PII checks; required error blocks with reason `timeout`; evidence absence blocks only when separately required; argument text contains keys and values in order; exactly 100,000 code points pass while 100,001 fail; input relevance raises configuration/validation error.
- **Prohibited side effects**: No remote/model call, logging of the synthetic email, normalization that changes the count, or optional override of a required failure.
- **Oracle provenance**: Manually reasoned directly from FR-07/08/12/17/18/33 and the policy table before running implementation.
- **Red evidence**: `tests/unit/test_core_contract.py` produced six behavioral assertion failures on 2026-09-28, with no import or environment failure.
- **Green evidence**: The same six assertions passed in `.venv/bin/python -m pytest -q tests/unit/test_core_contract.py` on 2026-09-28, without changing expectations.

## Foundation: preparation and safe records

- **Requirements**: FR-19, FR-24, FR-27, AC-19, AC-29.
- **Authority**: FR-19's setup validation, FR-24's record fields, and the constitution's privacy rule.
- **Fixture rationale**: Default required PII with no detector; injected local detector without external provider; default PII plus enabled relevance without evaluator; a record carrying synthetic content and credential sentinels. The relevance fixture retains PII because FR-08 requires local inspection before remote checks.
- **Expected outcomes**: Missing detector yields `local_pii_unavailable`; local-only preparation succeeds and prepares the detector; enabled remote check without evaluator yields `evaluator_unavailable`; record contains check/policy/outcome and unknown cost but no sentinels.
- **Prohibited side effects**: No provider probe, no remote call, and no sensitive data in exceptions or records.
- **Oracle provenance**: Derived from FR-19/24/27 and AC-19/29 before execution.
- **Red evidence**: Initial local preparation and record assertions failed behaviorally in targeted pytest on 2026-09-28.
- **Green evidence**: The preparation and record assertions passed in the 37-test local suite.

## Foundation: async lifecycle and record identifiers

- **Requirements**: FR-06, FR-24, FR-25, FR-27; AC-19, AC-20.
- **Authority**: Sync/async parity, explicit lifecycle, and routine-record content exclusion.
- **Fixture rationale**: Local fake detector under async preparation; closed guard reuse; a synthetic email embedded in policy or reason identity.
- **Expected outcomes**: Async preparation validates/prepares the detector and async close closes the guard; closed guard cannot be reused; content-bearing IDs cannot enter records.
- **Prohibited side effects**: No provider probe, raw sentinel, or successful reuse after close.
- **Oracle provenance**: Manually reasoned from FR-06/24/25/27 before executing the implementation.
- **Red evidence**: Async preparation and policy-identity assertions failed behaviorally in targeted pytest on 2026-09-28.
- **Green evidence**: Both passed in the 37-test local suite.

## Foundation: strict identity and exception safety

- **Requirements**: FR-07, FR-08, FR-14–FR-19, FR-27, FR-34.
- **Authority**: Policy uniqueness, privacy-first external disclosure, confidence validity, and content-free exception rules in the spec and constitution.
- **Fixture rationale**: Duplicate check IDs, a relevance output check without output PII, non-finite/over-one confidence, a policy ID containing synthetic email content, and an exception reason containing the same sentinel.
- **Expected outcomes**: All invalid fixtures fail before evaluation; known reason codes are preserved; optional evaluation error remains non-blocking while required violation/inconclusive reasons remain distinct.
- **Prohibited side effects**: No external call and no raw sentinel in routine exception text.
- **Oracle provenance**: Derived from FR-07/08/17/19/27/34 and the constitution before test execution.
- **Red evidence**: Three behavioral failures occurred before policy, decision, and error validation changes on 2026-09-28.
- **Green evidence**: Corresponding assertions passed in the 37-test local suite.

## Foundation: policy field types and immutability

- **Requirements**: FR-07, FR-18–FR-19; AC-14, AC-29.
- **Authority**: Policy table and immutable settings contract.
- **Fixture rationale**: Unknown check kind, numeric required flag, and mutable check collection.
- **Expected outcomes**: All are rejected during policy construction before protected work.
- **Prohibited side effects**: No model, detector, or evaluator call.
- **Oracle provenance**: Direct type and immutability requirements, fixed before test execution.
- **Red evidence**: Unknown-kind assertion failed behaviorally in `tests/unit/test_policy_models.py` on 2026-09-28.
- **Green evidence**: All field-type assertions passed in the 37-test local suite.

## Foundation: assembled native text

- **Requirements**: FR-08–FR-10, FR-33, AC-14, AC-34.
- **Authority**: The spec's supported text forms, ordered parts, JSON key/value rule, and inclusive 100,000-code-point limit.
- **Fixture rationale**: System and user messages with two ordered text parts, a tool description, a nested argument key containing synthetic PII, evidence text, an image part, an opaque object, an unknown role, and an over-limit string.
- **Expected outcomes**: Extract all seven ordered text pieces; reject image, opaque object, unknown role, and 100,001-code-point content before disclosure. Count tool argument keys toward the same limit.
- **Prohibited side effects**: No stringification, dropped part, normalization, remote call, or model call.
- **Oracle provenance**: Manually derived from FR-33 and Native Integration Coverage before implementation execution.
- **Red evidence**: Four behavioral assertions failed before extraction validation was implemented on 2026-09-28.
- **Green evidence**: Content tests passed in the 37-test local suite.

## Core input and output ordering

- **Requirements**: FR-03–FR-04, FR-08–FR-10, FR-15–FR-18; AC-02–AC-05, AC-15–AC-16.
- **Authority**: The spec's local-first ordering and required/optional policy table.
- **Fixture rationale**: A controlled detector recognizes `secret@example.com`; a controlled semantic evaluator counts calls; a safe request passes; a required finding blocks before evaluator; an optional finding records a violation; a candidate answer containing the sentinel blocks delivery.
- **Expected outcomes**: The required input or output finding blocks with zero evaluator calls. Optional finding allows with a recorded violation. Safe content is allowed unchanged. Repeated input evaluation inspects each changed snapshot.
- **Prohibited side effects**: No external judgment after required PII finding, no answer regeneration, no raw content in result or exception.
- **Oracle provenance**: Manually derived from the spec's acceptance cases before implementation.
- **Red evidence**: Three behavioral assertions failed with importable guard stubs in `tests/privacy/test_core_boundaries.py` on 2026-09-28.
- **Green evidence**: All three passed in the 28-test local suite after core orchestration was implemented.

## Pre-generation retrieved evidence privacy

- **Requirements**: FR-03, FR-08, FR-10–FR-11; AC-03, AC-05, AC-33.
- **Authority**: The spec requires all assembled retrieval text to pass local PII before a model submission; generation identity scopes output groundedness evidence, not pre-generation input inspection.
- **Fixture rationale**: An input context has one explicitly identified retrieved evidence item containing a synthetic email, but no generation ID has been assigned yet.
- **Expected outcomes**: Required input PII blocks and the semantic evaluator receives zero calls. The same case is checked in ordinary and async guard operations.
- **Prohibited side effects**: No remote evaluator or answer-model submission of the retrieved text, and no silent omission caused by the missing generation ID.
- **Oracle provenance**: Derived from the assembled-input and evidence-scoping rules before the guard fix.
- **Red evidence**: Pending intended assertion run.
- **Green evidence**: Pending implementation and suite run.

## Record metadata validation

- **Requirements**: FR-24, FR-27; AC-19, AC-26.
- **Authority**: The spec's restricted routine-record fields and content exclusion.
- **Fixture rationale**: Synthetic email in evaluator and error category, negative cost, and an ordinary unknown cost.
- **Expected outcomes**: Content-bearing metadata and invalid cost are rejected; unknown cost remains null.
- **Prohibited side effects**: No raw value in a routine record or exception.
- **Oracle provenance**: Derived from the spec's record fields before implementation.
- **Red evidence**: Metadata assertion failed in `tests/privacy/test_sanitized_records.py` on 2026-09-28.
- **Green evidence**: All metadata assertions passed in the 37-test local suite.

## Local PII setup

- **Requirements**: FR-08, FR-19, FR-28; AC-15, AC-28, AC-29.
- **Authority**: Research R3's offline `english-v1` preset and explicit model provisioning.
- **Fixture rationale**: The spaCy model is absent in the project virtual environment; preparation must identify the missing asset without download or network access.
- **Expected outcomes**: Local preparation raises `ConfigurationError` with stable `pii_model_unavailable` and sends no HTTP request.
- **Prohibited side effects**: No system Python package installation, runtime model download, or content-bearing exception.
- **Oracle provenance**: Spec and research decision recorded before executing implementation.
- **Red evidence**: Unsupported-language assertion failed behaviorally in `tests/contracts/test_local_pii.py` on 2026-09-28.
- **Green evidence**: Both local-setup tests passed after implementing explicit preset validation and model-presence checks.

## Local PII categories

- **Requirements**: FR-08, FR-28; AC-02, AC-28.
- **Authority**: Research R3's curated English preset and Presidio recognizer contracts.
- **Fixture rationale**: Synthetic person, email, North American phone, test credit card, valid-pattern US SSN, and benign instruction.
- **Expected outcomes**: The five category fixtures produce findings; the benign instruction does not. Detector setup and first use make no network connection.
- **Prohibited side effects**: No runtime asset download or external content disclosure.
- **Oracle provenance**: Fixed from stated category coverage and recognizer semantics before contract test execution.
- **Red evidence**: The category fixture was added after the detector implementation and has no valid prior red evidence; it remains a coverage test rather than a completed constitutional task.
- **Green evidence**: All five category fixtures and the benign near-match passed offline with the pinned model in `.venv`.

## Core async parity and setup failure privacy

- **Requirements**: FR-06, FR-19, FR-25, FR-27; AC-20, AC-29.
- **Authority**: Async core surface and sanitized setup failures in the Python SDK contract.
- **Fixture rationale**: Equivalent safe and blocked request contexts on ordinary and async methods, plus a detector whose setup exception contains a synthetic credential.
- **Expected outcomes**: Async and ordinary methods return equivalent decisions; setup failure is a `ConfigurationError` with a safe reason.
- **Prohibited side effects**: No credential in public exception and no unawaited coroutine.
- **Oracle provenance**: Derived from FR-06/19/25/27 and the Python SDK contract before implementation.
- **Red evidence**: Async parity and setup sanitization both failed behaviorally in `tests/unit/test_guard_lifecycle.py` on 2026-09-28.
- **Green evidence**: Both passed in the 37-test local suite.

## Groundedness evidence association

- **Requirements**: FR-11–FR-12, FR-17; AC-07–AC-08, AC-17.
- **Authority**: Only identified evidence associated with the answer's generation step can ground it.
- **Fixture rationale**: A saved candidate with an unrelated old evidence item, then an item associated with its generation ID.
- **Expected outcomes**: Old evidence yields a groundedness skip; matching evidence reaches the evaluator alone. Neither result is fabricated as a pass.
- **Prohibited side effects**: No unrelated evidence sent to the evaluator.
- **Oracle provenance**: Manually derived from FR-11/12 before implementation execution.
- **Red evidence**: The evaluator received old and current evidence in the first targeted test run on 2026-09-28.
- **Green evidence**: It received only current evidence after the fix; the test passed in the 37-test local suite.

## Jev response wire validation

- **Requirements**: FR-14, FR-17, FR-27, FR-30; AC-09, AC-18, AC-30.
- **Authority**: OpenRouter's official generated Decisions response and choice-answer types, inspected on 2026-09-28, plus the provider contract.
- **Fixture rationale**: One named choice answer with valid confidence; unknown answer key, model, label, and missing confidence.
- **Expected outcomes**: Only the exact named `pass`/`violation` choice with finite confidence in `[0,1]` becomes a check result. Invalid shapes raise a sanitized evaluation error.
- **Prohibited side effects**: No raw response in exceptions and no pass on malformed data.
- **Oracle provenance**: Hand-authored from the official response type and provider contract before parser implementation.
- **Red evidence**: Valid-choice assertion failed against the importable parser stub; malformed cases already failed closed.
- **Green evidence**: Six provider response cases passed after strict parsing was implemented.

## Jev one-question request and custom criteria privacy

- **Requirements**: FR-08–FR-09, FR-27, FR-30; AC-04, AC-09.
- **Authority**: Official OpenRouter Decisions request/choice-question/provider preference types and provider contract.
- **Fixture rationale**: One relevance question, fixed current request and answer, and synthetic PII in a custom criterion.
- **Expected outcomes**: Request has one choice question with explicit `pass`/`violation`, separated instructions/state, no session/user/trace fields, and fallback disabled. A required local PII finding in criterion prevents evaluator invocation.
- **Prohibited side effects**: No external request for contaminated criteria and no automatic telemetry identifier.
- **Oracle provenance**: Hand-authored from official wire types and FR-08/09 before implementation.
- **Red evidence**: Request-shape and custom-criterion privacy assertions failed behaviorally in targeted tests.
- **Green evidence**: Both passed after request construction and criterion preflight changes.

## Semantic confidence and available metadata

- **Requirements**: FR-17, FR-24; AC-18–AC-19.
- **Authority**: Default semantic minimum 0.80 and preservation of available judgment metadata.
- **Fixture rationale**: Controlled scores 0.80 and 0.79 with evaluator, usage, and cost.
- **Expected outcomes**: Equality passes; below minimum is inconclusive; valid metadata survives to the check result.
- **Prohibited side effects**: No fabricated zero cost or fabricated evaluator rationale.
- **Oracle provenance**: Derived from provider contract before implementation execution.
- **Red evidence**: Available metadata was dropped in the first targeted test run.
- **Green evidence**: Threshold equality, below-threshold uncertainty, and metadata preservation passed in the local suite.

## Bounded one-attempt provider transport

- **Requirements**: FR-19, FR-25, FR-30, FR-33; AC-09, AC-29–AC-31.
- **Authority**: Provider contract's 0.1–120 second total deadline and 512/256 KiB wire limits; HTTPX documents separate inactivity timeouts, and AnyIO documents cancellation scopes.
- **Fixture rationale**: Mock transport counts attempts and returns a valid response, immediate 429, slow response, or oversized body; invalid timeout and oversized request are local cases.
- **Expected outcomes**: One attempt for a valid call; completed 429 fails immediately; total deadline cancels slow work; over-limit request fails before attempt and over-limit response fails during read.
- **Prohibited side effects**: No retry, redirect, fallback, or raw body in errors.
- **Oracle provenance**: Fixed from FR-30 and provider contract before transport implementation.
- **Red evidence**: Nine deadline, limit, and error assertions failed against the importable transport stub.
- **Green evidence**: Nine async mock-transport cases passed; a separate local sync portal smoke returned a valid mock response.

## Async semantic evaluator lifecycle

- **Requirements**: FR-06, FR-17, FR-25, FR-30; AC-18, AC-20, AC-31.
- **Authority**: Python SDK contract's separate async preparation and protected methods.
- **Fixture rationale**: Async-only evaluator with preparation, one scored relevance judgment, and close; local detector remains synchronous.
- **Expected outcomes**: Async preparation calls evaluator's async setup, one async judgment yields allow, and async close runs. No synchronous evaluator method is required.
- **Prohibited side effects**: No blocking portal in the async host loop and no duplicate evaluator call.
- **Oracle provenance**: Derived from FR-06 and lifecycle contract before implementation.
- **Red evidence**: Async-only evaluator preparation assertion failed in targeted pytest.
- **Green evidence**: Async-only evaluator preparation, one judgment, and close passed.

## Guard to Jev async wiring

- **Requirements**: FR-08–FR-09, FR-17, FR-30; AC-04, AC-18, AC-31.
- **Authority**: Local-first guard contract and one-question provider wire.
- **Fixture rationale**: A safe saved answer with a controlled HTTP choice pass, and a PII-bearing answer with the same prepared evaluator.
- **Expected outcomes**: Safe answer makes one request and allows; PII-bearing answer blocks before the request.
- **Prohibited side effects**: No provider call for blocked output, no duplicate attempt, and no answer rewrite.
- **Oracle provenance**: Derived from FR-08/09/30 before evaluator wiring.
- **Red evidence**: Safe controlled Jev answer was blocked by the evaluator stub in targeted pytest.
- **Green evidence**: Controlled safe and PII-blocked async guard cases passed with one and zero HTTP attempts respectively.

## Provider failure ownership

- **Requirements**: FR-16, FR-19, FR-25, FR-30, FR-34; AC-09–AC-10, AC-34.
- **Authority**: Configuration/integration faults are outside optional check outcomes; post-setup provider timeout is an evaluation error.
- **Fixture rationale**: Optional relevance check with a controlled provider timeout and then an integration extraction failure.
- **Expected outcomes**: Timeout is a non-blocking recorded `evaluation_error` with its stable reason; integration fault propagates and stops regardless of optionality.
- **Prohibited side effects**: No integration failure downgraded to an optional outcome and no arbitrary exception text in records.
- **Oracle provenance**: Derived from FR-16/19/34 and the SDK exception table before implementation.
- **Red evidence**: Timeout reason was lost and optional integration fault was downgraded in two failing assertions.
- **Green evidence**: Both failure-ownership assertions passed after preserving provider reason and propagating integration faults.

## Complete context bounds

- **Requirements**: FR-26, FR-33; AC-14, AC-34.
- **Authority**: 100,000 code points, 128 messages, and 64 identified evidence items per context, inclusive.
- **Fixture rationale**: Sixty-five identified evidence items whose generation IDs differ from the active answer, and 64 matching items at the limit.
- **Expected outcomes**: Sixty-five are rejected before any check or disclosure even when none are scoped for groundedness; 64 are accepted when text and message limits pass.
- **Prohibited side effects**: No silent omission of over-limit evidence.
- **Oracle provenance**: Derived from the data model's per-context limit before implementation.
- **Red evidence**: The 65th unrelated evidence item was silently omitted from the count in targeted pytest.
- **Green evidence**: All identified evidence now counts; exact 64 and overflow cases passed.

## Saved-evaluation metrics

- **Requirements**: FR-20–FR-23; AC-13, AC-25.
- **Authority**: The spec's independently calculated seven-example confusion table.
- **Fixture rationale**: One true violation, one missed violation, one false alarm, two correct passes, one error, one skip.
- **Expected outcomes**: Seven total, five classified, one error, one skip; accuracy 3/5, precision 1/2, recall 1/2, false-positive rate 1/3, classified coverage 5/7. Zero denominators yield null.
- **Prohibited side effects**: No invented correctness for errors, skips, or unlabeled items.
- **Oracle provenance**: Counts copied from AC-25 and manually mapped to labels before implementation.
- **Red evidence**: Two independent count and undefined-denominator assertions failed against the metrics stub.
- **Green evidence**: The seven-example AC-25 fixture and undefined ratios passed.

## Versioned saved-example loader

- **Requirements**: FR-20–FR-21, FR-26–FR-27; AC-13–AC-14, AC-24.
- **Authority**: Saved Evaluation contract's UTF-8 JSONL schema and per-record error rule.
- **Fixture rationale**: A valid version-one record with one scoped label, malformed JSON line, duplicate example ID, and a later valid record.
- **Expected outcomes**: Valid records parse in order; individual bad lines produce sanitized errors and do not abort later records. Duplicate scoped labels and oversized content are invalid.
- **Prohibited side effects**: No answer generation, relabeling, or raw line text in error records.
- **Oracle provenance**: Derived from the evaluation contract before implementation.
- **Red evidence**: The ordered valid/error/duplicate/valid fixture failed against the loader stub.
- **Green evidence**: Versioned JSONL, per-line continuation, duplicate label, and context-limit tests passed.

## Saved-answer parity and continuation

- **Requirements**: FR-20–FR-21, FR-25, FR-27; AC-12–AC-13, AC-24.
- **Authority**: Live and saved evaluation share the guard and reducer, without regeneration.
- **Fixture rationale**: One safe answer and one PII-bearing answer using a controlled detector; a saved-line error is interleaved.
- **Expected outcomes**: Offline output decisions equal direct guard output decisions for the same contexts; the invalid line yields a sanitized error and later examples continue. Candidate answers remain unchanged.
- **Prohibited side effects**: No model generation or raw request/answer in result records.
- **Oracle provenance**: Derived from FR-20/21 and evaluation contract before implementation.
- **Red evidence**: Three-record parity fixture failed against the empty runner stub.
- **Green evidence**: Direct and saved decisions matched while invalid lines continued and candidate answers were unchanged.

## Content-free saved reports and comparison

- **Requirements**: FR-22–FR-24, FR-27; AC-13, AC-19, AC-24, AC-26.
- **Authority**: Saved Evaluation contract's per-example JSON, CSV aggregate, and two-setting comparison schema.
- **Fixture rationale**: Blocked saved answer contains a synthetic email; result has no cost; two fixed policy results differ on one example.
- **Expected outcomes**: JSON and CSV show safe IDs, outcomes, null cost, counts, and changed decision identity; no raw answer or content hash.
- **Prohibited side effects**: No raw request/answer/evidence, credentials, or arbitrary evaluator rationale in exports.
- **Oracle provenance**: Derived from FR-22/24/27 before report implementation.
- **Red evidence**: JSON and comparison assertions failed against report stubs; a later injected-reason privacy assertion also failed.
- **Green evidence**: Sanitized JSON, CSV, comparison, and injected-metadata rejection tests passed.

## Saved comparison aggregate counts

- **Requirements**: FR-22–FR-23; AC-24–AC-25.
- **Authority**: The saved-evaluation contract requires aggregate counts on each side of a two-settings comparison.
- **Fixture rationale**: One fixed example is allowed on the left and blocked on the right; neither side has a processing error.
- **Expected outcomes**: Changed example IDs contain that example; left counts are allow 1, block 0, error 0; right counts are allow 0, block 1, error 0.
- **Prohibited side effects**: No raw answer, synthetic email, or cost fabrication in the comparison.
- **Oracle provenance**: Manually counted from the fixed fixture and contract before the comparison fix.
- **Red evidence**: `test_csv_aggregate_and_comparison_use_safe_ids` failed with missing `left_counts` on 2026-09-28.
- **Green evidence**: The comparison tests passed after adding counts; the full deterministic suite passed 85/85 on 2026-09-28.

## Saved comparison identity integrity

- **Requirements**: FR-23, FR-27; AC-24, AC-26.
- **Authority**: The saved-evaluation contract requires a fixed ordered dataset, stable safe IDs, and content-free exports.
- **Fixture rationale**: Use a synthetic email as an example ID, then two rows with the same safe ID, then the same IDs in reversed order.
- **Expected outcomes**: Each malformed comparison is rejected before a report is returned.
- **Prohibited side effects**: No content-bearing ID in comparison output and no silent row overwrite or misleading changed-decision count.
- **Oracle provenance**: Derived from the fixed-dataset and privacy requirements before changing comparison validation.
- **Red evidence**: The unsafe-ID assertion failed behaviorally before comparison validation on 2026-09-28.
- **Green evidence**: Unsafe, duplicate, and reordered IDs were rejected; the full suite passed 86/86 on 2026-09-28.

## US5 controlled saved-evaluation acceptance run

- **Requirements**: FR-20–FR-24, FR-26–FR-27; AC-12–AC-13, AC-24–AC-26.
- **Authority**: The fixed seven-example AC-25 table and saved-evaluation contract, with labels and denominators established before implementation execution.
- **Fixture rationale**: Combine versioned UTF-8 JSONL valid/error lines, direct/live parity, two declared settings on the same saved candidate, the seven-row labeled metric fixture, and content-free report export with synthetic request/answer/evidence sentinels.
- **Expected outcomes**: No answer regeneration; direct and saved decisions agree; the same candidate can have changed decisions under two settings without mutating the first policy. The seven-row metrics remain 3/5 accuracy, 1/2 precision, 1/2 recall, 1/3 false-positive rate, and 5/7 classified coverage. Reports preserve safe identities and unknown cost without raw content, content hashes, credentials, or evaluator rationale.
- **Prohibited side effects**: No generated candidate, relabeling, fabricated accuracy for unclassified rows, raw report content, or hidden changed-setting identity.
- **Oracle provenance**: The existing AC-25 arithmetic and saved-evaluation sections above; the expanded settings/report fixtures were authored from those contracts before this focused run.
- **Red evidence**: Loader, runner, metrics, report, and comparison stubs have behavioral red evidence in their dedicated sections; the new settings-ID report assertion also failed before propagation.
- **Green evidence**: The focused 13-test US5 contract/acceptance/metrics/privacy run passed on 2026-09-28. Statistical quality evaluation remains a separate release gate.

## Request and evidence identity privacy

- **Requirements**: FR-11, FR-24, FR-27; AC-17, AC-26.
- **Authority**: Stable safe identifiers and exclusion of raw PII from records/provider metadata.
- **Fixture rationale**: Synthetic email in request and evidence IDs, alongside a valid safe ID.
- **Expected outcomes**: Content-bearing IDs are rejected at context construction; safe IDs are accepted.
- **Prohibited side effects**: No leaked identifier in diagnostic records or provider metadata.
- **Oracle provenance**: Derived from data-model and privacy rules before implementation.
- **Red evidence**: Content-bearing request ID was accepted in targeted pytest.
- **Green evidence**: Request, evidence, and generation identity validation passed.

## Native model-bound tool text

- **Requirements**: FR-08, FR-10, FR-33; AC-03, AC-14, AC-34.
- **Authority**: Native snapshot contract's tool descriptions and nested JSON string key/value inspection.
- **Fixture rationale**: A safe user message and a model-bound tool argument with a synthetic email key.
- **Expected outcomes**: Required local PII blocks before a model handoff; tool descriptions and argument strings count toward content limit.
- **Prohibited side effects**: No omission or stringification of the argument and no model call.
- **Oracle provenance**: Derived from FR-33 before implementation.
- **Red evidence**: A nested tool-argument email key was omitted from guard preflight in targeted pytest.
- **Green evidence**: The tool-key preflight assertion passed after snapshot fields were connected.

## Text-part boundary preservation for detection

- **Requirements**: FR-08, FR-10, FR-33; AC-03, AC-28, AC-34.
- **Authority**: Local PII must inspect each supported part without omission, while the 100,000-code-point limit counts only source content.
- **Fixture rationale**: Current request `hello` followed by a separate tool part beginning `secret@example.com`; a regex detector requiring a word boundary reproduces recognizer behavior.
- **Expected outcomes**: The email is detected and blocks before model submission; inserted inspection separators do not count toward the source-content limit.
- **Prohibited side effects**: No concatenation that turns the separate email into `hellosecret@example.com` and misses it.
- **Oracle provenance**: Derived from part-order and local PII requirements before implementation; confirmed by a runnable Microsoft example.
- **Red evidence**: Separate request and tool parts hid an email from a boundary-sensitive detector in targeted pytest.
- **Green evidence**: Separated and concatenated inspection views passed the boundary test; the Microsoft retrieval example blocked.

## LangChain native model and final hooks

- **Requirements**: FR-01–FR-06, FR-31–FR-34; AC-01–AC-04, AC-20, AC-23, AC-33.
- **Authority**: Pinned LangChain `ModelRequest`, `ModelResponse`, and middleware hook signatures plus the integration contract.
- **Fixture rationale**: Real native message/request/response objects, a tool argument key with synthetic PII, and a completed AI answer with synthetic PII.
- **Expected outcomes**: Safe model wrapper invokes handler exactly once and returns its original response; unsafe model-bound text invokes it zero times. Safe final hook returns no state update; unsafe final answer raises before delivery.
- **Prohibited side effects**: No duplicated model call, rewritten response, or leaked raw content.
- **Oracle provenance**: Pinned package type inspection and integration contract before implementation.
- **Red evidence**: Model-bound tool-key and final-answer PII assertions failed against native middleware stubs.
- **Green evidence**: Both native hook tests passed; async hook tests also passed.

## LangChain real agent and streaming boundary

- **Requirements**: FR-01–FR-06, FR-26, FR-31–FR-32; AC-01–AC-04, AC-20, AC-23.
- **Authority**: Pinned LangChain `create_agent` and the native integration contract.
- **Fixture rationale**: Real fake-chat agent with safe and PII-bearing user/assistant messages; streaming facade called before execution.
- **Expected outcomes**: Safe invoke preserves returned native state; input PII blocks before the model advances; output PII blocks final return; stream raises configuration error before model work.
- **Prohibited side effects**: No duplicate model call or silently exposed stream.
- **Oracle provenance**: Pinned package behavior and contract fixed before facade implementation.
- **Red evidence**: The real-agent facade exposed streaming in targeted pytest.
- **Green evidence**: Real ordinary agent safe/input-block/output-block and stream-rejection cases passed; one real async smoke passed outside the sandbox.

## LangGraph declared model and final paths

- **Requirements**: FR-01–FR-06, FR-31–FR-34; AC-01–AC-04, AC-11, AC-22, AC-32–AC-33.
- **Authority**: Pinned LangGraph `StateGraph` and compiled graph edges plus integration contract.
- **Fixture rationale**: Real graph with direct and retrieval branches joining a guarded model node and a guarded final node; a bypass branch reaches END without final guard.
- **Expected outcomes**: Safe graph returns native state, input PII prevents model node call, output PII prevents return, stream rejects before execution, and bypass topology fails at setup.
- **Prohibited side effects**: No model call after input block or unguarded final branch.
- **Oracle provenance**: Derived from pinned StateGraph edges and contract before implementation.
- **Red evidence**: Input block and bypass-topology assertions failed against graph helper stubs.
- **Green evidence**: Real direct/retrieval graph and bypass-rejection tests passed.

## Microsoft native async middleware

- **Requirements**: FR-01–FR-06, FR-31–FR-34; AC-01–AC-04, AC-20–AC-21, AC-32–AC-33.
- **Authority**: Pinned `agent-framework-core` `ChatMiddleware.process(ChatContext, call_next)` and `AgentMiddleware.process(AgentContext, call_next)` signatures plus integration contract.
- **Fixture rationale**: Native `Message` objects after provider-added text, one chat callback counting calls, and an `AgentResponse` carrying final text.
- **Expected outcomes**: Chat input PII prevents callback, safe chat calls once without altering result; final PII blocks return after callback; streaming rejects before callback.
- **Prohibited side effects**: No duplicate native call, output rewrite, or missed provider-added text.
- **Oracle provenance**: Pinned package source and framework pipeline documentation inspected before implementation.
- **Red evidence**: Chat and agent final PII assertions failed against native middleware stubs.
- **Green evidence**: Native context, real Agent, and provider-added message cases passed.

## Microsoft guarded facade and provider middleware order

- **Requirements**: FR-26, FR-31–FR-32; AC-21–AC-23, AC-33.
- **Authority**: Pinned Agent/ChatMiddlewareLayer pipeline order and the integration contract's later-mutator rule.
- **Fixture rationale**: Real Agent with a context provider adding safe messages, one adding chat middleware, and a streaming run request.
- **Expected outcomes**: Safe provider messages reach the guarded client; a provider adding later chat middleware fails before client invocation; streaming rejects before protected work.
- **Prohibited side effects**: No unguarded late mutation or model call after known incompatible provider setup.
- **Oracle provenance**: Pinned framework pipeline inspection and FR-32 before facade implementation.
- **Red evidence**: Streaming entry was exposed by the facade stub in targeted pytest.
- **Green evidence**: Streaming and later provider middleware were rejected before client invocation; provider-added message text remained guarded.

## LangGraph async guarded node arrangement (convergence)

- **Requirements**: FR-06, FR-31, FR-34; AC-32, AC-34.
- **Authority**: `coerce_to_runnable` in `langgraph._internal._runnable` wraps a callable object whose `__call__` is a coroutine function as `RunnableCallable(None, thing)` (native `.afunc` path, no executor thread); a plain synchronous callable becomes `RunnableCallable(thing, executor_wrapped_thing)`. Inspected directly against the pinned `langgraph==1.2.12` source before implementation, independent of running the adapter.
- **Fixture rationale**: A `GuardedModelNode`/`GuardedFinalNode` constructed with an `async def` `submit`/`context` callback exercises the mismatch: the node's own `__call__` stays synchronous, so LangGraph runs it in a worker thread, and calling the async callback there returns an un-awaited coroutine instead of the state dict.
- **Expected outcomes**: Constructing `GuardedModelNode`/`GuardedFinalNode` with a coroutine-function `assemble`, `submit`, or `context` argument raises `ConfigurationError("async_callable_unsupported")` immediately, before the node ever runs. A new `AsyncGuardedModelNode`/`AsyncGuardedFinalNode` pair accepts only coroutine-function callbacks, exposes an `async def __call__` using `aenforce_input`/`aenforce_output`, and is recognized by `compile_guarded_graph` through the node runnable's `.afunc` slot (LangGraph's native async-node path) so `ainvoke` runs it directly instead of in a thread pool.
- **Prohibited side effects**: No returned-but-unawaited coroutine ever reaches graph state; no model/final call happens before the guard fault is raised; the existing synchronous node path (still run through LangGraph's executor-thread `afunc` wrapper for `ainvoke`) is unchanged.
- **Oracle provenance**: Derived from the pinned `langgraph` wrapping behavior read above and from FR-34/AC-34's incompatible-arrangement rule, before writing the fix.
- **Red evidence**: Constructing `GuardedModelNode`/`GuardedFinalNode` with an async callback did not raise; invoking the compiled graph returned a `RuntimeWarning: coroutine ... was never awaited` and a downstream sanitized `IntegrationError` instead of a clear setup-time `ConfigurationError`. A new async node class did not exist at all.
- **Green evidence**: `GuardedModelNode`/`GuardedFinalNode` now reject async callbacks with `async_callable_unsupported` at construction; new `AsyncGuardedModelNode`/`AsyncGuardedFinalNode` require async callbacks and run through LangGraph's native `.afunc` path recognized by `compile_guarded_graph`; both the synchronous rejection and the async node execution/blocking/loop-identity cases pass in `tests/integration/test_langgraph.py`.

## Concurrent request isolation across core and native adapters (convergence)

- **Requirements**: FR-25; AC-21.
- **Authority**: Spec Key Entity "Evaluation context" ("must not mix concurrent requests") and FR-25 ("Concurrent evaluations MUST isolate content, policies, evidence, and records by request").
- **Fixture rationale**: `asyncio.gather` over several `aevaluate_output` calls on one shared `Guard`, each with a distinct `EvaluationContext`/evidence set and a recording evaluator that reports which evidence IDs it saw per call; a second case runs two `Guard` instances with different `PolicySet`s concurrently. Native-adapter cases run concurrent `ainvoke`/`arun` calls through LangGraph's new async node and the LangChain/Microsoft async facades with per-request distinguishing content (one safe, one PII-bearing) so a mix-up would flip an outcome.
- **Expected outcomes**: Each concurrent call's recorded evidence/result set contains only its own request's identifiers; a safe concurrent request is never blocked by another concurrent request's violation and vice versa; two concurrently prepared `Guard` instances with different policies never observe each other's check set.
- **Prohibited side effects**: No result, evidence id, or content string from one concurrent request appears in another's decision or recorded evidence-id list.
- **Oracle provenance**: Derived directly from FR-25/AC-21 before writing the test; the shared reducer and `EvaluationContext` are immutable per-call inputs (`core/models.py`, `core/decision.py`), so isolation was expected to already hold — this adds committed evidence rather than a design change.
- **Red evidence**: No test in the suite exercised concurrent overlapping requests before this task; the gap itself (missing coverage) was the red condition per the converge finding, not a behavioral failure.
- **Green evidence**: See `tests/unit/test_concurrency_isolation.py`, and the added concurrent cases in `tests/integration/test_langgraph.py`, `test_langchain.py`, and `test_microsoft.py`.

## LangChain real tool-calling retrieval journey (convergence)

- **Requirements**: AC-11, AC-32; FR-05, FR-10.
- **Authority**: Spec AC-11 ("intermediate requests to tools are not judged as final answers") and the Native Integration Coverage table's LangChain row ("Each assembled model request after supported context and middleware additions, before its model call").
- **Fixture rationale**: A scripted `BaseChatModel` subclass that first emits an `AIMessage` with a `tool_calls` entry (`bind_tools` accepted as a no-op so `create_agent` can call it), then on the second turn emits a plain text final answer, wired through a real `@tool`-decorated function whose result contains a PII sentinel.
- **Expected outcomes**: The first (tool-requesting) model turn is checked and allowed; the tool executes and its result is appended as a `ToolMessage`; the second assembled model request — now containing the tool's PII-bearing output — is independently rechecked by `InputGuardMiddleware` and blocked before that second model call ever happens (not merely before a third); the tool-call message itself is never treated as a final answer needing output-boundary checks.
- **Prohibited side effects**: No second model call happens once the recheck blocks; the tool's PII output never reaches the model.
- **Oracle provenance**: Derived directly from AC-11 and the coverage table before writing the test, and confirmed against `langchain==1.4.2`'s `create_agent`/middleware pipeline by reading `factory.py` (`_get_bound_model`, `wrap_model_call` invoked once per model turn).
- **Red evidence**: No test in the suite exercised a real tool-calling loop; `examples/langchain_agent.py` and `tests/integration/test_langchain.py` both used `tools=[]`. The gap itself was the red condition per the converge finding.
- **Green evidence**: See `test_real_tool_calling_loop_completes_when_tool_output_is_safe` and `test_real_tool_calling_loop_rechecks_second_model_request_with_tool_output` in `tests/integration/test_langchain.py`, and the updated `examples/langchain_agent.py`.
- **Discovered while implementing this task (not part of the original converge findings)**: running the example with the real `LocalPIIDetector` (not the tests' string-match fake) against the original literal example content (`"hello"` / `"safe"`) raised `PolicyViolationError` on the plain safe path. Cause: `Guard._inspection_text`/`assembled_input_text` append `"".join(parts)` (all parts concatenated with no separator) to the checked text, specifically to catch PII split across message-part boundaries; spaCy's `en_core_web_lg` NER then misreads the resulting run-together bare words (`"hellohellosafe"`) as a PERSON entity at 0.85 confidence, above the 0.35 default cutoff. This is a benign near-match / false-positive class the project's own quality gates (AC-26, `evaluations/manifests/v1.md`) already anticipate, not a policy-decision bug — no-separator concatenation is intentional split-PII coverage and isn't being changed here. Fixed for this example by using realistic multi-word sentences instead of bare single words, which do not trigger the misread (confirmed empirically); `examples/langgraph_agent.py` and `examples/microsoft_agent.py` were checked and did not hit this combination. Left open as a held-out-evaluation candidate under T081/T082 rather than adjusting detector heuristics under this task.

## Caller exception and cancellation identity through async adapter paths (convergence)

- **Requirements**: AC-20, AC-34; FR-25.
- **Authority**: FR-25 ("Cancellation and application failures MUST retain their meaning rather than become successful guard outcomes") and AC-34 ("Caller exceptions and cancellation retain their original meaning"). Already covered for the synchronous LangGraph node in `tests/unit/test_failure_taxonomy.py`; this closes the same coverage for the async paths.
- **Fixture rationale**: A protected host callback (`handler`/`call_next`/`submit`) that raises a plain `RuntimeError` or `asyncio.CancelledError` when invoked through `InputGuardMiddleware.awrap_model_call` (LangChain), `MicrosoftChatGuard.process`/`MicrosoftAgentGuard.process` (Microsoft), and the new `AsyncGuardedModelNode` (LangGraph).
- **Expected outcomes**: The identical exception instance/type propagates out of the guarded async call unchanged — not wrapped, not downgraded to an `IntegrationError` or `EvaluationError`, not swallowed. `CancelledError` in particular must never be reported as a passed or evaluated check.
- **Prohibited side effects**: No sanitized guard exception, check result, or record is produced for a caller failure; the guard's own async evaluation call is not re-entered after the callback fails.
- **Oracle provenance**: Derived from FR-25/AC-34 before writing the tests, following the same pattern already validated for the synchronous LangGraph node.
- **Red evidence**: No test in the suite exercised a caller exception or cancellation through any asynchronous adapter entry point; the LangChain/Microsoft/async-LangGraph code paths call the protected callback directly with no wrapping, so this is coverage for already-correct behavior, confirmed rather than newly implemented.
- **Green evidence**: See the added cases in `tests/contracts/test_native_adapters.py` and `tests/integration/test_langgraph.py`.

## Permitted native result metadata and state preservation (convergence)

- **Requirements**: AC-01, FR-02; SC-002.
- **Authority**: FR-02 ("Permitted execution MUST return the normal result unchanged; guards MUST NOT silently rewrite, regenerate, switch answer models, or duplicate protected execution") and AC-01 ("the application receives its normal result, metadata, and state effects").
- **Fixture rationale**: A LangChain `AIMessage` response carrying `response_metadata`, `usage_metadata`, and an explicit `id`, returned through a safe `create_guarded_agent(...).invoke` call; a LangGraph graph whose state carries an extra caller-defined key alongside `answer` that the guarded nodes never touch.
- **Expected outcomes**: The guarded LangChain facade's returned message preserves `response_metadata`, `usage_metadata`, and `id` unchanged (identity or equality, not just matching `.content`); the guarded LangGraph facade's returned state preserves the caller-defined extra key unchanged.
- **Prohibited side effects**: No metadata field is dropped, replaced, or regenerated by the guard on an allowed path.
- **Oracle provenance**: Derived directly from FR-02/AC-01 before writing the test; existing tests already assert unchanged `.content` but never metadata/extra-state fields, so this was a coverage gap rather than a known defect.
- **Red evidence**: No test in the suite asserted anything beyond final message text; the gap itself (missing coverage) was the red condition per the converge finding.
- **Green evidence**: See the added assertions in `tests/integration/test_langchain.py` and `tests/integration/test_langgraph.py`.

## LangChain user middleware placement cannot bypass the input guard (convergence)

- **Requirements**: FR-32, FR-34; plan: shared native extraction and topology validation.
- **Authority**: Pinned `langchain==1.4.2` `AgentMiddleware.wrap_model_call` nesting, confirmed by direct inspection before writing the test: registration order is outer-to-inner, so a middleware later in the list runs closer to the actual model call and receives whatever the outer middleware passed to `handler(...)`, including any mutation.
- **Fixture rationale**: `create_guarded_agent(...)` hardcodes `middleware=[OutputGuardMiddleware(guard), *middleware, InputGuardMiddleware(guard)]`, so a caller-supplied middleware always sits *outside* (before) `InputGuardMiddleware` in the call chain and can never be registered after it through this facade. A user middleware here mutates the assembled request to add PII-bearing text before calling `handler`.
- **Expected outcomes**: The mutated content — added by a middleware that runs before the guard — is still checked and blocked, because `InputGuardMiddleware` is the innermost wrapper and sees whatever the outer middleware passed on; there is no public arrangement through `create_guarded_agent` letting a later mutator run closer to the model than the guard.
- **Prohibited side effects**: No model call happens once the mutated content is blocked.
- **Oracle provenance**: Derived from FR-32/FR-34 before writing the test, and confirmed against the pinned middleware nesting order by direct inspection (not by running the agent_guard implementation) before asserting the expected outcome.
- **Red evidence**: No test in the suite exercised a user-supplied middleware mutating content before the guard; the gap itself was the red condition per the converge finding (F11/T052/T086), not a known defect — `create_guarded_agent`'s fixed ordering already prevented the unsafe arrangement by construction.
- **Green evidence**: See `test_user_middleware_mutation_before_guard_is_still_checked` in `tests/integration/test_langchain.py`.

## Cross-framework and offline final-answer decision parity (convergence)

- **Requirements**: AC-12, FR-20; SC-003.
- **Authority**: FR-20 ("Live and offline evaluation MUST apply the same policy definitions and decision rules... identical controlled judgments MUST produce identical decisions across supported integrations") and AC-12.
- **Fixture rationale**: One shared `Guard` (required local PII output check) and two fixed candidate answers — one safe, one PII-bearing — run through the final-output boundary of all four execution surfaces (core `evaluate_output`, LangChain `create_guarded_agent` via `OutputGuardMiddleware`, LangGraph `GuardedFinalNode`, Microsoft `MicrosoftAgentGuard`) and through `run_saved` offline evaluation of a `SavedExample` carrying the same candidate answer.
- **Expected outcomes**: For the safe answer, all five paths deliver/allow it unchanged; for the PII-bearing answer, all five paths block delivery with the same `pii_found` reason. No path silently passes what another blocks.
- **Prohibited side effects**: No answer is regenerated or rewritten on any path; the offline run does not mutate the live `Guard`'s policy.
- **Oracle provenance**: Derived directly from FR-20/AC-12 before writing the test — the four adapters and the offline runner already delegate to the same `Guard.evaluate_output`/`enforce_output`, so identical decisions were expected by construction; this adds committed cross-surface evidence rather than a design change.
- **Red evidence**: No test in the suite compared decisions *across* the four execution surfaces and offline evaluation for the same content; each integration test file only compares its own surface against the core guard in isolation (or not at all). The gap itself was the red condition per the converge finding.
- **Green evidence**: See `tests/acceptance/test_cross_framework_parity.py`.
