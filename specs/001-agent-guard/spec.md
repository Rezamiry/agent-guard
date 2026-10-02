# Feature Specification: Agent Guard — Input, Output, and Offline Policy Evaluation

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-09-23

**Status**: Draft — validated for planning

**Input**: Read the repository's existing Agent Guard product specification and implementation
plan, understand the intended library, and write a fresh feature specification.

Agent Guard lets application developers apply configurable checks before an agent sends content
to a model and before it delivers a final answer. Policy authors can evaluate the same rules
against saved conversations to understand blocking behavior, false alarms, and missed violations.
The library serves applications that answer directly or use retrieved information, commonly
called retrieval-augmented generation (RAG).

This specification synthesizes [the original product baseline](../../agent-guard-spec.md),
[the prior implementation plan](../../agent-guard-implementation-plan.md), and
[the constitution](../../.specify/memory/constitution.md). FR-01–FR-24 and AC-01–AC-14 retain
their original meanings. Additional identifiers capture observable safeguards already described
in the plan or constitution. This document is the active Spec Kit feature specification;
the source documents remain provenance, and technical proposals require verification during
planning. Any future divergence from the original behavioral baseline requires a recorded
specification amendment.

Amendment 2026-09-23: Resolve checklist findings CHK031 and CHK033 by distinguishing invalid
setup from runtime evaluation failures and adopting bounded, single-attempt external evaluation.
These decisions apply to live and saved-example evaluation; the local-PII-only default is unchanged.

Amendment 2026-09-27: Define per-integration native boundaries, content scope, limits, changed-input
rechecks, and adapter failures in FR-31–FR-34 and AC-32–AC-34. Runtime adapter failures are a
distinct explicit failure category under FR-19 and AC-14; they cannot be optional check outcomes.

## Clarifications

### Session 2026-09-23

- Q: Which checks should run by default when a developer enables Agent Guard without selecting individual checks? → A: Required local PII checks on input and output only; all other checks require explicit enablement.

## User Scenarios & Testing *(mandatory)*

All five stories are required for the first release. Priorities indicate delivery order, not
permission to omit a story. Enforcement scenarios use predetermined evaluation outcomes to
verify allow/block behavior independently of a detector's or model's judgment quality.

### User Story 1 - Protect content before external submission (Priority: P1)

An application developer attaches input protection so that prohibited personal information,
instruction-manipulation attempts, unsafe requests, and application-specific violations can
stop an affected model call. Protection covers the content actually sent, including conversation
history and information retrieved after the user's initial request.

**Why this priority**: A check performed after disclosure cannot protect the submitted content.

**Independent Test**: Run a guarded input flow with safe and prohibited examples and known check
outcomes. Observe whether external evaluation and answer generation occur, without needing
output scoring or offline reporting.

**Acceptance Scenarios**:

1. **AC-02** — **Given** a required local check detects prohibited personally identifiable
   information (PII) in input, **When** the application submits it, **Then** neither the external
   evaluator nor the affected answer model receives it, and records do not repeat the value.
2. **AC-03** — **Given** the initial message passes but later history or retrieved material
   introduces prohibited PII, **When** the assembled input is checked, **Then** submission of that
   content to the external evaluator and affected answer model is blocked.
3. **AC-05** — **Given** a required injection, content-safety, or custom input check returns a
   violation, **When** the input decision is made, **Then** affected answer generation does not
   proceed and the application receives a policy-violation exception.
4. **AC-15** — **Given** required local inspection is unavailable or fails, **When** protected
   content is submitted, **Then** evaluation fails explicitly before that content is sent to an
   external evaluator or answer model; remote inspection is not used as a fallback.
5. **AC-16** — **Given** a developer explicitly makes PII optional and its check returns a finding
   or error while required checks pass, **When** input is evaluated, **Then** processing may
   continue, the optional outcome is recorded without content, and the configuration is identified
   in documentation as monitoring rather than default PII blocking.
6. **AC-28** — **Given** a developer enables Agent Guard without selecting individual checks,
   **When** input and output are processed, **Then** only required local PII checks run at those
   boundaries. No external evaluator is called. Prompt-injection, content-safety, custom-policy,
   relevance, and groundedness checks run only after explicit enablement.

### User Story 2 - Deliver only answers permitted by the active policy (Priority: P1)

An application developer checks final answers for prohibited content, relevance to the current
request, and support from supplied evidence. Users receive the original permitted answer;
blocked answers are withheld rather than silently repaired.

**Why this priority**: Safe input does not ensure that a generated answer is safe or supported.

**Independent Test**: Supply saved candidate answers and known check outcomes at the output
boundary. Verify delivery decisions without generating new answers or requiring a retrieval flow.

**Acceptance Scenarios**:

1. **AC-04** — **Given** a generated answer contains PII detected as prohibited by a required
   policy, **When** output protection runs, **Then** the answer is withheld from both external
   output evaluation and the user, and diagnostics exclude the detected value.
2. **AC-06** — **Given** a final answer fails required relevance to the current request,
   **When** delivery is attempted, **Then** it is blocked. An unexpected or off-topic request
   alone is not rejected by an input-relevance check.
3. **AC-07** — **Given** identifiable evidence is available but a relevant answer fails required
   groundedness, **When** output is evaluated, **Then** delivery is blocked for lack of support.
4. **AC-08** — **Given** no evidence is available, **When** groundedness is evaluated, **Then** it
   is recorded as skipped, not passed. Delivery is blocked if evidence is separately required;
   otherwise the remaining required checks decide delivery.
5. **AC-11** — **Given** a conversation can answer directly or after retrieval, **When** either
   path produces a final answer, **Then** applicable output checks govern delivery on both paths;
   intermediate requests to tools are not judged as final answers.
6. **AC-17** — **Given** a follow-up request, identified retrieval evidence, and unrelated tool
   messages, **When** relevance and groundedness are assessed, **Then** relevance addresses the
   current request in context and groundedness uses only evidence associated with that answer.
   A retrieved instruction to ignore policy does not become a governing policy instruction.
7. **AC-27** — **Given** an answer violates required content-safety or custom output criteria,
   **When** delivery is attempted, **Then** it is blocked even if relevance and groundedness pass.
   When that same check is optional and all required conditions permit, delivery continues and
   the finding is recorded.

### User Story 3 - Configure policies and understand failures (Priority: P1)

A policy author selects the checks and boundaries that matter for an application, decides which
are required, and sets acceptance criteria. An operator can distinguish a confirmed violation
from an uncertain or failed evaluation without inspecting sensitive conversation content.

**Why this priority**: Applications need predictable behavior when judgments are uncertain or
services fail, and a monitoring check must not override required protection.

**Independent Test**: Apply required and optional policies to predetermined pass, violation,
inconclusive, error, and missing-evidence outcomes. Compare decisions and sanitized records
against the decision table without running a live chatbot.

**Acceptance Scenarios**:

1. **AC-09** — **Given** a required evaluator times out, supplies an unusable judgment, or lacks
   sufficient confidence, **When** its result is processed, **Then** the affected generation or
   delivery is blocked and the reason distinguishes an error or inconclusive result from a
   confirmed violation.
2. **AC-10** — **Given** equivalent failures affect only optional checks and required checks
   permit the action, **When** decisions are combined, **Then** processing continues and optional
   outcomes are recorded. An optional pass cannot override a required failure.
3. **AC-14** — **Given** an invalid policy, unsupported content form, or required capability that
   is absent, **When** protection is requested, **Then** the application receives an explicit
   configuration, integration, or evaluation failure and the case is never reported as passed.
4. **AC-18** — **Given** a valid judgment and a configured minimum confidence, **When** confidence
   equals the minimum, **Then** the judgment is accepted; below it the outcome is inconclusive.
   A confident violation still blocks when required. Missing or malformed required decision
   information cannot pass.
5. **AC-19** — **Given** checks with known outcomes and some unavailable metadata, **When** an
   operator reads the records, **Then** each includes the check, boundary, outcome, policy
   identity, elapsed time, available confidence and evaluator identity, and applicable error
   category. Unavailable cost is unknown, not zero; raw content and credentials are absent,
   and no explanation is attributed to an evaluator that did not supply it.
6. **AC-29** — **Given** an enabled check, whether required or optional, has an absent local
   dependency, missing required credentials, or invalid settings, **When** its configuration is
   validated, **Then** a configuration failure prevents protected execution and external evaluation
   from beginning. An omitted credential is not tested by contacting the provider. Disabled
   checks impose no dependency or credential requirements; default PII-only use needs no external
   evaluator credentials. A non-positive or non-finite external-evaluation deadline is invalid.
7. **AC-30** — **Given** an optional check passed configuration validation but its dependency later
   becomes unavailable, the provider rejects supplied credentials, or evaluation otherwise fails,
   **When** its judgment is attempted, **Then** an evaluation error is recorded and other required
   checks govern continuation. The same runtime failure on a required check blocks the affected
   action. Cancellation and caller errors retain their separate behavior under AC-20.
8. **AC-31** — **Given** a validly configured external check, **When** the provider rate-limits or
   rejects the attempt, or the finite elapsed-time deadline expires, **Then** the check reports an
   evaluation error after at most one provider attempt. Agent Guard does not wait for a retry
   window, retry, or switch evaluators. A required check blocks; an optional check records the
   error and permits continuation only if all required conditions permit it. A completed provider
   error is reported without waiting for the deadline.

### User Story 4 - Adopt protection without changing successful application behavior (Priority: P2)

A developer adds guards through the documented native integration for an existing agent
application. Normal permitted results retain their form, and developers can identify exactly
which execution boundaries are protected.

**Why this priority**: Useful protection must fit existing applications and remain reliable across
supported integrations and execution styles.

**Independent Test**: For each supported integration, exercise a minimal direct-answer and
retrieval-answer application with controlled checks. Compare allowed results with predetermined
native results and verify blocking, cancellation, and protection boundaries.

**Acceptance Scenarios**:

1. **AC-01** — **Given** acceptable input and output and required checks that permit processing,
   **When** the guarded operation completes, **Then** the application receives its normal result,
   metadata, and state effects without answer replacement or duplicate protected execution.
2. **AC-20** — **Given** equivalent ordinary and asynchronous supported flows, **When** guards
   permit or block them, **Then** decisions agree; cancellation and application errors remain
   distinguishable and are not converted into successful evaluations.
3. **AC-21** — **Given** overlapping requests with different policies and evidence, **When** they
   are evaluated, **Then** neither request uses or exposes the other's content, evidence, policy,
   or result records.
4. **AC-22** — **Given** a request for streaming or an unsupported integration arrangement,
   **When** the protected entry point can identify it, **Then** it rejects the request before
   protected execution rather than silently returning an unguarded stream. Documentation states
   where the library cannot observe later content changes or arbitrary application code.
5. **AC-23** — **Given** a developer follows the published installation and adoption example for
   one supported integration, **When** they run its safe and blocked cases, **Then** both outcomes
   are reproducible without the separate demonstration application or unrelated integrations.
   The release includes an explicit open source license and documented compatibility limits.
6. **AC-32** — **Given** each integration and execution surface in the Native Integration Coverage
   table, **When** a direct or retrieval-assisted path submits assembled input and later produces
   a final answer, **Then** the stated input and output boundaries are checked; allowed native
   results and state are preserved. Microsoft Agent Framework's native async path is required,
   without claiming a synchronous native agent path.
7. **AC-33** — **Given** history, retrieval, a context provider, or middleware changes model-bound
   content after an earlier check, **When** a supported path reaches model submission, **Then**
   the changed assembled content is checked before submission. If a later mutator can bypass that
   boundary and is identifiable at setup, the arrangement is rejected before protected execution;
   unobservable changes are documented as outside coverage.
8. **AC-34** — **Given** unsupported or oversized native content, an incompatible integration
   arrangement, or an adapter failure while extracting content or preserving native state,
   **When** protection is requested, **Then** the affected submission or delivery fails explicitly
   without treating the failure as an optional check result. An identifiable setup incompatibility
   is a configuration failure; an unexpected runtime adapter fault is an integration failure.
   Caller exceptions and cancellation retain their original meaning.

### User Story 5 - Evaluate saved examples and compare policy settings (Priority: P2)

An evaluation owner tests existing requests and candidate answers before changing production
policies. They can compare settings and distinguish enforcement correctness, detection quality,
false alarms, missed violations, and evaluation failures.

**Why this priority**: Policy changes need evidence of their effect before they affect users.

**Independent Test**: Evaluate a fixed saved dataset with independently assigned labels and known
judgments. Compare two policy settings and manually calculated report totals without generating
answers or running a live conversation.

**Acceptance Scenarios**:

1. **AC-12** — **Given** equivalent content, policy settings, and controlled evaluator responses,
   **When** each supported integration and offline evaluation process them, **Then** per-check
   outcomes and aggregate allow/block decisions agree.
2. **AC-13** — **Given** saved requests, candidate answers, optional evidence, and reference
   labels, **When** evaluated, **Then** reports distinguish correct decisions, missed violations,
   false alarms, inconclusive results, errors, and skips. Without labels, correctness metrics
   are unavailable rather than claimed as accuracy.
3. **AC-24** — **Given** two policy settings and a fixed saved dataset, **When** compared,
   **Then** the owner can identify changed per-example decisions and aggregate counts, with
   settings attached to each result, without regenerating answers or changing live policy.
4. **AC-25** — **Given** five classified examples with one true violation, one missed violation,
   one false alarm, and two correct passes, plus one error and one skip, **When** reported,
   **Then** the totals are seven examples, five classified, one error, and one skip. Accuracy
   among classified examples is 3/5, precision is 1/2, recall is 1/2, false-positive rate is 1/3,
   and classified coverage is 5/7. Undefined ratios are reported as undefined, not zero.
5. **AC-26** — **Given** a documented PII category/language preset, configurable safety starter
   policy, and a release evaluation against fixed reference labels and predeclared
   quality criteria, **When** evidence is published, **Then** it includes violations and benign
   near-matches, measured false alarms and missed violations, elapsed-time and available cost
   summaries, relevant versions, and known limits. Behavioral correctness and statistical
   judgment quality are reported separately.

### Edge Cases

- An early block prevents later checks from running: those checks are identifiable as not
  evaluated, never passed. Only the documented missing-evidence rule permits a required
  groundedness skip without a separate failure (AC-08, AC-09).
- Evidence is separately required even when groundedness itself is optional: the independent
  evidence requirement still blocks when evidence is absent (AC-08).
- A provider returns an unknown label, mismatched judgment, invalid confidence, or incomplete
  response: it is an evaluation error, never a pass (AC-09, AC-18).
- An input exceeds supported size or uses an unsupported language or content form: report the
  limitation explicitly; do not silently truncate, stringify, or omit uninspected content
  (AC-14, AC-22).
- A known later mutator that can change model-bound content after the last observable input check
  makes that integration arrangement unsupported; changed content on supported paths is checked
  again before submission (AC-33).
- A native adapter cannot extract protected content or preserve the permitted native result:
  prevent the affected submission or delivery and report an integration failure, not an optional
  policy result. Earlier host side effects are not reversed (AC-34).
- An output is blocked after generation or a tool side effect: withhold the answer without
  claiming to reverse prior costs, tool actions, persistence, or host tracing (AC-04, AC-11).
- An optional local PII check detects prohibited data: the configured monitoring behavior can
  permit external processing; documentation must state this reduced protection (AC-16).
- A refusal or clarification can be relevant to the current request. Benign discussion of an
  attack is not automatically an injection violation, and acknowledging absent evidence is not
  automatically fabrication. Quality evaluation includes these distinctions (AC-17, AC-26).
- Empty or partially labeled datasets and zero metric denominators: report counts, label and
  classification coverage, and unavailable metrics without inventing correctness (AC-13, AC-25).
- Cancellation during evaluation is not a safe result, and simultaneous requests must not share
  evaluation context (AC-20, AC-21).
- Missing setup dependencies or credentials for an enabled optional check are configuration
  failures; failures after valid setup are evaluation errors subject to required/optional rules.
  Disabled checks do not require those resources (AC-29, AC-30).
- Provider throttling does not trigger hidden waiting or another attempt. A stalled external
  judgment reaches its finite deadline and becomes an evaluation error; cancellation remains
  cancellation rather than a timeout or successful evaluation (AC-20, AC-31).

## Requirements *(mandatory)*

### Functional Requirements

The preserved identifiers below allow existing acceptance evidence and future tasks to remain
traceable. An input boundary is the point before an affected model submission; an output boundary
is the point before final delivery. External evaluation is itself a disclosure boundary.

- **FR-01**: Developers MUST be able to attach protection through supported native integration
  points without replacing their application's normal conversation and result conventions.
- **FR-02**: Permitted execution MUST return the normal result unchanged; guards MUST NOT silently
  rewrite, regenerate, switch answer models, or duplicate protected execution.
- **FR-03**: A required input violation, inconclusive judgment, or evaluation error MUST block the
  affected answer-model submission before that submission occurs.
- **FR-04**: A required output violation, inconclusive judgment, or evaluation error MUST block
  final delivery; blocking MUST NOT imply reversal of generation costs or earlier side effects.
- **FR-05**: Applicable final-answer checks MUST cover both direct and retrieval-assisted answers
  while excluding intermediate requests to tools from final-answer assessment.
- **FR-06**: Protection MUST support ordinary and asynchronous non-streaming usage on the supported
  execution surfaces, with equivalent policy decisions for equivalent inputs and judgments.
- **FR-07**: Policy authors MUST be able to enable the checks in the policy table below, choose
  valid input/output boundaries, configure criteria, and mark checks required or optional.
  Prompt-injection, content-safety, custom-policy, relevance, and groundedness checks MUST remain
  disabled until explicitly enabled. Providing a starter policy does not enable its checks.
- **FR-08**: PII inspection MUST occur locally before protected content reaches an external
  evaluator or answer model. Required local findings or failures MUST stop affected external
  processing. Default protection MUST enable only required local PII checks on input and output
  and MUST NOT call an external evaluator. Optional PII is explicit monitoring.
- **FR-09**: Generated output and other content included in external output evaluation MUST pass
  applicable local PII enforcement before external output evaluation and final delivery. Routine
  logs and exceptions MUST NOT disclose detected values.
- **FR-10**: Supported protection MUST account for assembled model input, including history and
  newly retrieved content. Entry-only coverage MUST NOT be advertised as complete protection.
- **FR-11**: Groundedness MUST assess an answer against identifiable evidence available to its
  generation step; conversation and unrelated tool messages MUST NOT automatically become evidence.
- **FR-12**: Absent evidence MUST yield a groundedness skip, never a pass. A separately configured
  evidence requirement MUST block delivery when evidence is absent; without it, other applicable
  required checks govern delivery.
- **FR-13**: The library MUST support output relevance to the current request in context and MUST
  NOT offer input-relevance rejection. Unexpected requests may still violate other policies.
- **FR-14**: Each check MUST distinguish pass, violation, inconclusive, evaluation error, and
  skipped outcomes; checks not run after an earlier block MUST NOT be reported as passed.
- **FR-15**: Applicable required violations, inconclusive judgments, and evaluation errors MUST
  block through exceptions whose reasons distinguish these outcomes.
- **FR-16**: Optional violations, inconclusive judgments, and evaluation errors MUST be recorded
  and MUST NOT alone block execution or delivery. This applies to failures after valid setup,
  including later dependency unavailability and provider rejection of supplied credentials;
  invalid setup remains a configuration failure under FR-19.
- **FR-17**: Confidence acceptance MUST be configurable per check. A valid judgment at or above
  the minimum meets that criterion; below it is inconclusive. Missing or malformed required
  decision information MUST NOT pass. Confidence MUST NOT be described as guaranteed correctness.
- **FR-18**: An action MUST be permitted only when every applicable required check permits it,
  subject to FR-12. Optional results MUST NOT override required failures.
- **FR-19**: Invalid policies, unsupported content, and unavailable configured required
  capabilities MUST cause explicit configuration, integration, or evaluation failures, never
  silent bypass.
  Before protected execution or external evaluation begins, every enabled check MUST be validated
  for required local dependencies, presence of required credentials, and valid settings. Missing
  setup prerequisites or invalid settings MUST raise a configuration failure even when the check
  is optional. This validation MUST NOT contact an external evaluator to test credentials.
  Disabled checks MUST NOT impose dependency or credential requirements. Failure of a dependency
  after valid setup, or rejection of supplied credentials by the provider, MUST be classified as
  an evaluation error and handled according to the check's required/optional status.
- **FR-20**: Live and offline evaluation MUST apply the same policy definitions and decision
  rules. Differences MUST be explainable using supplied content, settings, and evaluator identity;
  identical controlled judgments MUST produce identical decisions across supported integrations.
- **FR-21**: Offline evaluation MUST accept saved requests and candidate answers, optional
  evidence, and optional reference labels, including relevant conversation context. It MUST be
  possible to evaluate an existing answer without generating a replacement.
- **FR-22**: Reports MUST separate classified policy outcomes, inconclusive judgments, errors,
  and skips. With independent labels they MUST expose correct decisions, false alarms, and missed
  violations, with denominators and coverage. Without labels, correctness is unavailable; undefined
  ratios MUST remain undefined. Aggregate blocking MUST be distinct from confirmed violations.
- **FR-23**: Evaluation owners MUST be able to compare policy settings, including confidence
  criteria, against fixed saved examples and inspect changed decisions without altering live policy.
- **FR-24**: Operational records MUST identify check, boundary, outcome, policy version or settings,
  elapsed time, available confidence and evaluator identity, and applicable error category.
  Available usage/cost MUST be reported; unavailable values MUST NOT be substituted with zero.
- **FR-25**: Concurrent evaluations MUST isolate content, policies, evidence, and records by
  request. Cancellation and application failures MUST retain their meaning rather than become
  successful guard outcomes.
- **FR-26**: The library MUST document supported content, execution boundaries, and limitations;
  identifiable unsupported streaming MUST be rejected before protected execution. Oversized
  content MUST fail explicitly rather than be silently reduced to a supported size.
- **FR-27**: Routine diagnostic and evaluation records MUST exclude raw conversation content,
  detected PII values, and credentials. They MUST give outcome reasons without fabricating an
  evaluator explanation unavailable from the judgment.
- **FR-28**: The release MUST supply a documented PII category/language preset and configurable
  content-safety starter policy. Only validated detection coverage may be advertised; published
  evaluation MUST disclose benign near-matches, missed violations, false alarms, and limitations.
- **FR-29**: The library MUST be usable independently of the separate demonstration application
  and unrelated integrations. Releases MUST provide an explicit open source license, installation
  instructions, compatibility limits, and working safe/block examples for every promised integration.
- **FR-30**: Each external judgment for an enabled check at a boundary in a live request or saved
  example MUST make at most one provider attempt, subject to prior privacy and configuration
  checks. Agent Guard MUST NOT automatically retry, wait for a provider retry window, or switch
  evaluators. Every attempt MUST have a positive, finite elapsed-time deadline that bounds the
  total wait for that judgment, not only periods of inactivity. Timeout, provider rejection,
  throttling, and service unavailability MUST produce evaluation errors governed by FR-15–FR-16;
  completed errors MUST NOT be held until the deadline. Cancellation remains governed by FR-25.
- **FR-31**: Each promised integration MUST protect the native input and final-output boundaries
  and execution surfaces in the Native Integration Coverage table. Unsupported native surfaces
  MUST NOT be represented as protected; permitted native results, metadata, and state effects
  MUST remain unchanged.
- **FR-32**: A supported integration MUST check the final assembled model-bound content after
  history, retrieval, context-provider, and middleware additions, including changes after an
  earlier check. If an identifiable later mutator can bypass the last observable check, setup
  MUST reject that arrangement before protected execution. Documentation MUST name content
  changes the integration cannot observe.
- **FR-33**: The initial native content scope and size limits are defined below. Supported text
  MUST be inspected without dropping or flattening its native structure; non-text or opaque
  model-bound content MUST fail explicitly. Limits apply before affected external evaluation or
  model submission, with an exact-limit value accepted and an over-limit value rejected.
- **FR-34**: An identifiable incompatible native arrangement MUST cause a configuration failure
  before protected execution. An unexpected runtime adapter failure in content extraction,
  boundary identification, or native result/state preservation MUST cause a distinct integration
  failure and stop affected submission or delivery, regardless of whether policy checks are
  optional. Such failures MUST NOT be recorded as policy passes, violations, or optional
  evaluation errors; caller exceptions and cancellation MUST retain their original meaning.

### Native Integration Coverage

| Integration | Required input boundary | Required final-output boundary | Supported non-streaming surface |
| --- | --- | --- | --- |
| LangChain | Each assembled model request after supported context and middleware additions, before its model call. | Completed agent answer after supported output transformations, before return to the caller. | Ordinary and asynchronous native agent use. |
| LangGraph | Each declared model submission after graph state, retrieval, and node input are assembled, before its model call; graph arrangements must expose that boundary. | Each declared final-answer-producing path, including direct and retrieval branches, before the answer is returned. | Ordinary and asynchronous native graph use. |
| Microsoft Agent Framework Python | Each chat-model request after context-provider additions, before its model call. | Completed agent result before delivery to the caller. | Native asynchronous agent use; an ordinary script may run an async entry point. |

The v1 native content scope is text strings and native text parts in system, user, assistant, and
tool messages; developer messages are included where a supported framework exposes them. It also
includes textual retrieved evidence, model-bound tool descriptions, and string keys and values
within JSON-compatible tool arguments. Numeric and Boolean tool-argument values retain their structure
but contain no text to inspect. Images, audio, video, binary attachments, and opaque objects that
may contain model-bound content are unsupported. No adapter may silently stringify a native
object, discard a text part, or treat an uninspected form as safe. The same content scope applies
to content used in external output evaluation and to final answers before delivery.

An assembled evaluation context may contain at most 100,000 Unicode code points of supported
text, including tool-argument keys and values, 128 messages, and 64 identified evidence items.
Count code points without Unicode normalization; each text occurrence counts once in the assembled
content sent at that boundary. A value at any one limit is accepted if
all other limits are satisfied; a value above any limit is rejected explicitly before affected
external evaluation or model submission. The public compatibility documentation must identify
any narrower framework-specific limit before claiming that framework arrangement is supported.

### Policy Coverage and Enforcement

Only local PII checks are enabled by default, required on both input and output. All other
checks in the table are available for explicit enablement; supported scope does not imply
default activation. This default prevents external evaluation calls, not permitted calls to
the host application's answer model.

| Check | Supported scope | User-visible purpose |
| --- | --- | --- |
| Prompt injection | Input, including assembled untrusted context | Identify attempts to override instructions or bypass policy. |
| PII | Input and output | Identify configured prohibited personal-information categories locally before disclosure. |
| Content safety | Input and output | Apply a configurable starter policy for harmful assistance, targeted abuse, and sexual exploitation while allowing benign discussion. |
| Custom policy | Input, output, or both | Apply the author's explicitly defined application rules. |
| Relevance | Output only | Judge whether the answer addresses the current request in conversation context. |
| Groundedness | Output with identified evidence | Judge support for the answer's claims in supplied evidence, without certifying the evidence as true. |

| Check outcome | Required check | Optional check |
| --- | --- | --- |
| Pass | Permit only if other required conditions permit. | Record and continue. |
| Violation | Block with a violation exception. | Record and continue. |
| Inconclusive | Block with an inconclusive exception. | Record and continue. |
| Evaluation error | Block with an evaluation-failure exception. | Record and continue. |
| Groundedness skipped for absent evidence | Record the skip; permit only if evidence is not separately required and other required conditions permit. | Record the skip; a separate evidence requirement still blocks. |

Configuration failures prevent processing even for optional checks: missing setup dependencies,
omitted required credentials, and invalid settings are not monitoring outcomes. Failures after
valid setup, including provider rejection of supplied credentials, follow the evaluation-error
row. Disabled checks require no setup resources. A skip caused by an earlier block does not
reopen a blocked action. Live blocking raises the applicable exception; offline reports
record the corresponding decision for the saved example without treating a policy block as a
failure of the entire evaluation exercise.

### Acceptance Traceability

| Requirements | Acceptance scenarios |
| --- | --- |
| FR-01, FR-02 | AC-01, AC-12, AC-23 |
| FR-03, FR-07, FR-08, FR-10 | AC-02, AC-03, AC-05, AC-15, AC-16, AC-27, AC-28 |
| FR-04, FR-09 | AC-04, AC-06, AC-07, AC-27 |
| FR-05, FR-06 | AC-11, AC-20 |
| FR-11, FR-12, FR-13 | AC-06, AC-07, AC-08, AC-17 |
| FR-14, FR-15, FR-16, FR-17, FR-18 | AC-08, AC-09, AC-10, AC-16, AC-18, AC-30, AC-31 |
| FR-19 | AC-14, AC-15, AC-22, AC-29, AC-30 |
| FR-20, FR-21, FR-22, FR-23 | AC-12, AC-13, AC-24, AC-25 |
| FR-24, FR-27 | AC-02, AC-04, AC-19, AC-26 |
| FR-25, FR-26 | AC-20, AC-21, AC-22 |
| FR-28, FR-29 | AC-23, AC-26 |
| FR-30 | AC-29, AC-31 |
| FR-31 | AC-32 |
| FR-32 | AC-33 |
| FR-33, FR-34 | AC-34 |

### Key Entities *(include if feature involves data)*

- **Policy**: An identifiable set of check criteria with a version or settings identity,
  applicable boundary, required/optional status, confidence criteria, and any evidence requirement.
- **Evaluation context**: The current request, relevant conversation, candidate answer when
  applicable, and evidence belonging to that evaluation; it must not mix concurrent requests.
- **Evidence item**: Identifiable source content explicitly associated with answer generation.
  Its presence establishes what can be checked for support, not that the source is true.
- **Check result**: A policy's outcome at a boundary, sanitized reason, available confidence,
  timing, evaluator identity, and usage or error information.
- **Saved example**: A request and candidate answer with optional conversation context, evidence,
  and independent reference labels; it can be evaluated without answer generation.
- **Evaluation report**: Per-example results and aggregate decisions, settings identities,
  counts, label/classification coverage, quality metrics when justified, and measured overhead.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across all supported integrations, 100% of controlled required input-block cases
  prevent the affected answer submission, and 100% of required output-block cases prevent delivery.
  Required local PII-block cases make zero subsequent external disclosures of affected content.
- **SC-002**: In 100% of controlled allow cases, callers receive the expected unchanged result
  with no duplicate protected execution. Each of the three supported integrations demonstrates
  both a direct-answer and a retrieval-answer journey using its published adoption instructions.
- **SC-003**: Every required/optional outcome combination and missing-evidence configuration
  matches the decision table; equivalent controlled cases achieve 100% decision agreement
  across live integrations and offline evaluation.
- **SC-004**: An evaluation owner can compare two settings on one saved dataset without
  regenerating any answer or changing live settings. All per-example changes remain attributable
  to the settings evaluated, and all independently calculated report counts and ratios agree.
- **SC-005**: All diagnostic privacy cases disclose zero supplied sensitive-content or credential
  sentinels in routine records and exceptions. All concurrency cases show zero cross-request
  context mixing; cancellation cases yield no falsely successful evaluations.
- **SC-006**: Each advertised check has release evidence covering both violations and benign
  near-matches. The report separates behavioral correctness from judgment quality, meets quality
  criteria fixed before the held-out evaluation, and discloses all errors, skips, and denominators.
- **SC-007**: Release evaluation reports added elapsed time and available usage/cost for every
  supported check category and integration, with sample counts and evaluation conditions.
  Missing measurements are explicitly identified. No unmeasured latency, cost, or accuracy
  guarantee is advertised.

The 100% criteria above concern controlled behavioral cases, not universal real-world detection.
All acceptance scenarios must pass for release; quality criteria and evaluation datasets must be
fixed independently before their assessment, as required by the constitution.

## Assumptions

- **Compatibility commitments**: The existing project baseline requires an open source Python
  library with LangChain, LangGraph, and Microsoft Agent Framework integrations in the first
  release. These names define user-facing compatibility scope, not newly selected architecture.
  Ordinary and asynchronous use follows each integration's supported execution surfaces.
- **Judgment dependency**: Jev through OpenRouter is the initial external evaluator. The host
  application's answer provider remains independent. Provider access is needed for live remote
  judgments; offline evaluation means evaluation of saved examples, not a promise of no network.
  Deterministic acceptance evidence must not require live provider access.
- **External evaluation limits**: FR-30 fixes one attempt, no retry-window waiting, no evaluator
  fallback, and evaluation-error classification for timeout and throttling. Before external
  evaluator implementation and its acceptance tests, planning must select and document the
  finite deadline default, permitted configuration range, units, and elapsed-time measurement
  boundary. These choices must bound total waiting and preserve cancellation; they are operational
  limits, not promises of judgment latency or service availability.
- **Local privacy dependency**: A suitable local PII capability is required for default protection.
  Exact category/language coverage, confidence presets, and compatible dependency versions must
  be verified and documented during planning. The native content scope and context limits in
  FR-33 must be checked against selected dependencies before implementation and release claims.
  No specific detector or universal recognition rate is assumed.
- **Application responsibility**: The host supplies relevant context and identifies evidence and
  final-answer boundaries. Documentation must state unsupported arrangements. Guards do not
  erase existing host logs or persisted state, or reverse actions already performed.
- **Quality and performance**: The source baseline sets no numerical latency, cost, or universal
  accuracy targets. Planning must establish the evaluation datasets, calibration procedure, and
  predeclared quality criteria before measurement; values must not be inferred from results to
  make a run pass. Development data and held-out evaluation labels remain separate.
- **Scope exclusions**: Streaming, general HTTP interception, separate tool-action authorization,
  approval workflows, rollback, automatic redaction or rewriting, regeneration, model switching,
  human escalation, input relevance, user-defined violation callbacks, dashboards, and hosted
  monitoring are outside v1. Additional providers/frameworks, a separate .NET package, and a
  dedicated CI integration are not release commitments. The later RAG demonstration application
  belongs in a separate project.
- **Planning authority**: The earlier plan supplies context for observable safeguards, not a
  mandate to reuse its classes, transport, directory layout, or tooling. The next planning phase
  must verify external contracts and retain the constitution's independent-test-expectation rule.
