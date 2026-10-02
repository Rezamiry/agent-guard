# Research: Agent Guard Python SDK

Date: 2026-09-23; revised 2026-09-27 for FR-31–FR-34 and AC-32–AC-34. Input: [spec.md](spec.md) and the repository constitution.
Decisions below are design commitments. Documentation/package metadata inspection is not an
installation test, a compatibility certification, or a measurement of detection quality.

## R1 — Python package and compatibility baseline

**Decision:** Build `agent_guard` as a typed Python library using Python 3.11 and 3.12 initially
(`requires-python >=3.11,<3.13`), a `src/` layout, Hatchling, and a committed uv development lock.
Use Pydantic 2 (`>=2.12.5,<3`) for strict public/data-file validation, HTTPX `>=0.28,<0.29` and
AnyIO `>=4.8,<5` for opt-in external judgments. Frameworks and Presidio are optional installation
extras. Base import needs neither a detector model nor evaluator credentials; preparing the
default protective configuration requires the local PII extra and model.

Initial integration pins selected from published package metadata: `langchain==1.4.2`,
`langchain-core==1.6.4`, `langgraph==1.2.12`, `agent-framework-core==1.19.0`.
Do not advertise broader ranges until their endpoints pass compatibility tests. Implementation
must resolve and commit all transitive pins in `uv.lock`; no lock or installed environment is
claimed by this planning run. CI validates both Python versions and each installation extra.
Initial supported platform is Linux x86-64; other platforms remain unclaimed until validated.

**Rationale:** A narrow initial compatibility matrix is reproducible and keeps native integrations
optional. uv supports extras and checked lock consistency; dependency resolution and installation
are explicit implementation gates. [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/).

**Alternatives considered:** A hosted guard service changes the library scope. Installing every
framework in the base package prevents independent adoption. Claiming every upstream Python
version without integration evidence would overstate compatibility.

Package evidence: [LangChain](https://pypi.org/project/langchain/1.4.2/),
[LangChain core](https://pypi.org/project/langchain-core/1.6.4/),
[LangGraph](https://pypi.org/project/langgraph/1.2.12/),
[Microsoft core](https://pypi.org/project/agent-framework-core/1.19.0/).

## R2 — Pure decisions and explicit lifecycle

**Decision:** Separate immutable policy/context/results, a pure decision reducer, local detector,
remote provider, and native adapters. One shared orchestration algorithm handles live and saved
examples. `Guard.prepare()` / `await Guard.aprepare()` validate all enabled capabilities locally;
no provider probes are allowed. Methods called before preparation raise configuration errors.
Use explicit close/aclose lifecycle; the preparation mode selects sync or async resources.

Default `PolicySet` contains required local PII for input/output only. Semantic checks require
explicit enabling. A guarded disclosure boundary must include local PII inspection; it may be
required or explicitly optional, but remote evaluation cannot bypass that inspection. Disabled
semantic checks create no provider/dependency requirements. Reject policies that disable PII
while asking the SDK to claim a protected model/evaluator disclosure boundary.

Missing enabled dependencies/model assets, absent credentials, invalid configuration, duplicate
policy identities, or unsupported policy scopes fail preparation even for optional checks.
A later detector/provider failure is a result governed by required/optional status. Never catch
caller operation errors or cancellation in a blanket evaluator-error handler.

**Rationale:** This implements FR-08 and FR-16/FR-19 without conflating optional monitoring with
invalid setup. Stable machine reasons support content-free diagnostics.
**Alternatives considered:** Adapter-specific reducers would diverge; treating missing setup as
an optional runtime failure conceals installation errors. Automatic setup downloads violate the
local-only default.

## R3 — Local PII and offline provisioning

**Decision:** Select `presidio-analyzer==2.2.364`, spaCy `>=3.8,<3.9`, and installed
`en_core_web_lg==3.8.0`. The `english-v1` preset supports `en` and these entity categories:
PERSON, EMAIL_ADDRESS, PHONE_NUMBER (US/CA/GB regions), CREDIT_CARD, US_SSN. Default recognizer
score cutoff is 0.35; this is an initial detector setting, not a confidence probability.
Do not advertise physical street addresses, all government identifiers, or other languages.

Use an explicitly curated local recognizer registry. The spaCy adapter must load only the
already installed pinned model and fail locally when it is missing/incompatible. It must not
invoke Presidio's automatic model download. Provide an SDK-owned email recognizer using
`TLDExtract(suffix_list_urls=(), cache_dir=None, fallback_to_snapshot=True)`; do not globally
monkeypatch tldextract. No runtime network is permitted in local detection, including first use
with an empty cache. Model provisioning is a documented installation-time action.

**Rationale:** Presidio's default spaCy loader may download assets, and its email recognizer uses
tldextract, whose default behavior can fetch suffix data. Explicit adapters close these paths.
Presidio/spaCy recognizer scores are not calibrated probabilities; local PII result confidence
is null, and semantic confidence thresholds on local PII are rejected as invalid settings.

**Alternatives considered:** Regex-only inspection lacks name recognition. Remote inspection
would disclose uninspected content. The small English model may reduce installation size but
requires separate quality evidence before substitution.

Sources: [Presidio metadata](https://raw.githubusercontent.com/microsoft/presidio/2.2.364/presidio-analyzer/pyproject.toml),
[spaCy engine](https://raw.githubusercontent.com/microsoft/presidio/main/presidio-analyzer/presidio_analyzer/nlp_engine/spacy_nlp_engine.py),
[email recognizer](https://raw.githubusercontent.com/microsoft/presidio/2.2.364/presidio-analyzer/presidio_analyzer/predefined_recognizers/generic/email_recognizer.py),
[tldextract offline configuration](https://github.com/john-kurkowski/tldextract/blob/master/README.md),
[model metadata](https://raw.githubusercontent.com/explosion/spacy-models/master/meta/en_core_web_lg-3.8.0.json),
[supported entities](https://presidio.dataprivacystack.org/supported_entities/).

## R4 — External judgment contract

**Decision:** Send one choice question per remote check to
`POST https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.13`, bearer authentication,
with `provider.allow_fallbacks=false`. Use raw HTTPX rather than the provider SDK, because the
SDK's Decisions method has automatic retry behavior. Disable transport retries and redirects.
The original documentation reference was unavailable; the official generated SDK models and
method supply the inspected wire contract. See [provider contract](contracts/provider.md).

Map `pass` and `violation` labels only. Require exactly the requested answer identity and a finite
confidence in [0,1]. Upstream permits absent confidence; Agent Guard treats it as an evaluation
error. A valid score below the configured minimum yields inconclusive. Initial semantic minimum
is 0.80, configurable in [0,1]. Keep policy instructions separate from untrusted `state`; this is
structural separation, not proof of resistance to prompt injection. Scan all outbound evaluation
content locally, including custom criteria if they contain supplied text.

**Rationale:** Explicit choice mapping prevents unvalidated natural-language judgments from
becoming permission. Record the actual model/version returned; unexpected model identity fails
closed as a provider contract error. Cost absent upstream remains unknown.
**Alternatives considered:** Chat-completion prompting is a different contract; provider SDK
retries violate FR-30. A latest-model alias makes quality evidence unstable.

Sources: [Decisions method](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/decisions.py),
[request](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionsrequest.py),
[choice question](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionschoicequestion.py),
[choice answer](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionschoiceanswer.py),
[response](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionsresponse.py),
[provider options](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/providerpreferences.py),
[Jev overview](https://openrouter.ai/docs/guides/community/jev),
[confidence meaning](https://docs.typesafe.ai/confidence).

## R5 — Deadlines, resource limits, and cancellation

**Decision:** Remote timeout defaults to 10.0 seconds; accepted range is 0.1–120.0 finite seconds.
Measure with a monotonic clock from evaluator invocation, before resource/portal queueing, until
complete body receipt, decoding, and validation. Use an absolute deadline with AnyIO's cancel
scope around asynchronous HTTPX. Check remaining time before sending and after decoding; never
accept a late judgment. Completed HTTP errors, including 429, become immediate evaluation errors.

Sync preparation owns a persistent AnyIO blocking portal; sync calls submit the same cancellable
async operation and wait on the future only for the remaining deadline. Expiry cancels the task.
Portal startup/shutdown belong to explicit guard lifecycle, not each request's timeout path.
Async preparation owns resources in the caller's async context. Do not wrap synchronous HTTP in
an abandoned worker thread or share async clients across loops. Cleanup must be bounded; no
unbounded shield or implicit retry. Ordinary scheduling overhead is not a hard-real-time guarantee.

SDK limits: 100,000 total Unicode code points of supported text per context, counted without
normalization and including tool-argument keys; 128 messages; 64 evidence items;
512 KiB serialized outbound request and 256 KiB inbound response. Apply limits before disclosure
and as responses are read; reject overflow without truncation. Equality with a limit is allowed
when all other limits pass. These are SDK operational choices, not claims about provider maximums.
Inspect every native text part in supported message roles, textual evidence, model-bound tool
descriptions, and all string keys and values of JSON-compatible tool arguments while retaining structure.
Binary/image/audio/video and opaque model-bound parts are rejected, never stringified or dropped.
Saved datasets are iterated one example
at a time; default concurrency is one, with caller-controlled concurrency through independent
request contexts. No cross-request judgment cache.

**Rationale:** HTTPX's individual timeouts bound connection/read/write/pool inactivity, not total
judgment time. A cancel scope plus a synchronous deadline waiter closes that gap.
**Alternatives considered:** `future.result(timeout)` on blocking HTTP leaves network work alive;
per-chunk read timeouts permit endless trickle responses; nested event loops break host applications.

Sources: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/),
[AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html),
[AnyIO blocking portals](https://anyio.readthedocs.io/en/stable/threads.html).

## R6 — Native integration boundaries

**Decision:** LangChain uses native `wrap_model_call` / `awrap_model_call` for assembled input
and `after_agent` / `aafter_agent` for final output. Separate input and output middleware instances:
input guard last in the list (closest to model), output guard first (last after-agent observer).
Inspect system message separately from request messages, retaining role and text-part order, plus
all model-bound textual tool definitions and nested string keys and values in JSON-compatible arguments.
Reject known later mutators that invalidate the placement contract. Recheck any supported
model-bound content changed after an earlier guard decision before submission.

LangGraph uses native input/output guard nodes in an explicit topology: assembly -> input guard
-> model, and every final-answer branch -> output guard -> END. The model must consume exactly
the inspected assembled snapshot; a node decorator alone cannot see a privately assembled prompt.
A non-streaming Runnable facade preserves invoke/ainvoke inputs, config, keyword arguments, and
output. Guard nodes return an empty state update on allow. Evidence extractors require registered
source identity; arbitrary tool output is not evidence.

Both Runnable integrations expose a non-streaming facade rejecting stream/astream/event-stream
entry before protected work. Direct bypass of the facade is outside its documented coverage.
Microsoft uses `AgentMiddleware.process(AgentContext, call_next)` and
`ChatMiddleware.process(ChatContext, call_next)`, awaiting `call_next()` without a context argument.
Chat-level inspection observes context-provider additions; agent middleware checks final results.
Microsoft's native run surface is async; ordinary scripts use an async main, not an invented sync
agent API. All adapters preserve native results, state updates, metadata, cancellation, and errors.
The framework matrix in [spec.md](spec.md) is the v1 product scope: LangChain and LangGraph
ordinary/async non-streaming use; Microsoft native async use. Every declared input boundary
must see the exact assembled content consumed by the model. A graph guard placed before a node
that privately builds a different prompt does not satisfy this condition. A known unobservable
late mutator is rejected at setup; genuinely unobservable application changes remain a
documented limitation, never a complete-protection claim.

An identifiable incompatible arrangement raises a configuration failure before protected
execution. An unexpected adapter extraction, boundary-identification, or native result/state
preservation fault raises a distinct integration failure and prevents affected submission or
delivery even if all policy checks are optional. It is not a policy-check result. Caller
exceptions and cancellation propagate without reclassification. This separation avoids an
optional check silently masking failure of the protective integration itself.

**Rationale:** Native layers let input and final-output protection observe the right content while
retaining host conventions. Core sync/async APIs do not require every framework to offer both.
**Alternatives considered:** Generic chatbot signatures lose native state; node-only coverage misses
late prompts; treating every model reply as final incorrectly grades tool requests.

Sources: [LangChain middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom),
[LangGraph graphs](https://docs.langchain.com/oss/python/langgraph/graph-api),
[Microsoft middleware](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/middleware/),
[Microsoft pipeline](https://learn.microsoft.com/en-us/agent-framework/agents/agent-pipeline),
[Microsoft implementation source](https://github.com/microsoft/agent-framework/blob/main/python/packages/core/agent_framework/_middleware.py).
Pinned-package public-interface inspection corroborates these hooks; executable compatibility
and middleware ordering remain implementation acceptance gates. Current Microsoft concept docs
and some generated API reference pages show different callback/context names; the installed
pinned package, not a latest-version page, must decide the exact callable signature.

## R7 — Saved evaluation, identity, and diagnostics

**Decision:** Import versioned UTF-8 JSONL saved examples; export sanitized JSON report and CSV
summary. Labels attach to `(example_id, policy_id, boundary)` and mean `pass` or `violation`.
An omitted label is unknown, not pass. Do not infer per-policy labels from an overall answer label.
Use immutable policy identity plus a canonical settings fingerprint; persist no context or raw
model output in reports. Caller-supplied display labels, arbitrary error text, model rationale,
content hashes, and raw policy criteria are excluded from routine diagnostics.

Produce per-policy/boundary confusion counts among labeled classified records, classified coverage
among all records, label coverage, and independent aggregate allow/block counts. Undefined ratios
are null. Compare two settings on the same ordered dataset without replacing live configuration.
One blocked example does not abort the dataset. Invalid global policy configuration aborts before
processing; invalid individual records receive sanitized error records and processing continues.
No database, telemetry service, or mandatory CLI is introduced.

**Rationale:** Explicit label scope prevents ambiguous metrics; content-free reports avoid copying
sensitive evaluation datasets into logs. The host controls source-file storage and deletion.
**Alternatives considered:** Automatic label inference and implementation-derived snapshots create
untrustworthy accuracy claims; persisting all prompts increases disclosure without a requirement.

## R8 — Independent quality gates and release readiness

**Decision:** Freeze a rubric and fixture manifest before implementation for controlled cases.
For statistical evaluation reserve, per advertised PII category and per semantic check category,
100 positive and 100 benign near-match held-out cases, separately from at least 50+50 development
cases. Split by source/template family; labels require independent human review and provenance.
Fixture authors must not derive answers from the implementation or evaluator under assessment.

Predeclared dataset gates: each PII category recall >=0.90, false-positive rate <=0.05, classified
coverage >=0.99; each semantic category recall >=0.90, false-positive rate <=0.10, classified
coverage >=0.95. Also publish aggregate false blocks (including required uncertainty/errors) and
missed blocks, so confident-only metrics cannot conceal availability costs. All categories must
pass individually; report counts, denominators, uncertainty intervals, latency distribution, and
available cost. These are project release gates, not universal accuracy guarantees. Statistical
quality failure blocks release, not Phase 1 design; no results exist yet.

Tune only on development cases. Holdout results cannot justify relabeling or weakening thresholds;
a substantive change requires a separately reserved new holdout and a recorded decision. Detector
cutoff and semantic confidence default are versioned policy settings.

Use pytest, pytest-asyncio, Hypothesis, Ruff, mypy, build and twine checks. Deterministic tests
prohibit external network/API keys and use handwritten wire fixtures plus real framework objects.
TDD evidence is independent expected behavior -> intended assertion failure -> implementation ->
green -> refactoring; missing imports alone do not count as red.

**Rationale:** Controlled software correctness and uncertain statistical detection need distinct
acceptance evidence. **Alternatives considered:** Live outputs as golden labels, retuning against
holdout, and an aggregate score that hides failing categories violate the constitution.

## R9 — Open source distribution

**Decision:** Propose Apache-2.0 for project source and use SPDX metadata, third-party notices,
contribution instructions, compatibility notes, and migration notes in the release work package.
This plan does not add a license or assert maintainer ratification. Maintainer acceptance of the
license and dependency/model redistribution review are release gates. The model is separately
provisioned, not silently bundled or downloaded at runtime.

**Rationale:** Makes the licensing deliverable explicit without misrepresenting the constitution
as selecting a license. **Alternatives considered:** An unlabeled public repository is insufficient
for the promised open source package. License review is a release decision, not a missing runtime
architecture choice.

## Research completion

All architecture questions required for Phase 1 have decisions above. Remaining work is measured
verification: dependency resolution/lock, both Python environments, all native integrations,
local offline network isolation, transport deadlines, and frozen-dataset quality gates. None is
claimed to have passed during this planning-only run. No product requirement has been dropped.
