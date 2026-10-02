<!--
Sync Impact Report — temporary review material; remove before committing.
Version change: unratified scaffold → 1.0.0 (initial adoption)
Modified principles:
- Principle 1 placeholder → I. Reusable Library and Native Integration
- Principle 2 placeholder → II. Privacy Before External Processing
- Principle 3 placeholder → III. Explicit and Consistent Enforcement
- Principle 4 placeholder → IV. Independent Oracles and Test-Driven Development
- Principle 5 placeholder → V. Honest Evaluation and Safe Observability
Added sections: populated Core Principles; Open Source and Compatibility;
Development Workflow and Release Gates; Governance.
Removed sections: none.
Deferred placeholders / follow-up TODOs: none.
Scope: only this constitution is updated; dependent templates read it at runtime.
-->

# Agent Guard Constitution

## Core Principles

### I. Reusable Library and Native Integration

Agent Guard MUST remain an independently usable, open source Python library for guarding
agent inputs and outputs. Core policy contracts and enforcement rules MUST be independent of
application code and framework adapters. Framework dependencies MUST be optional so core users
need not install every supported framework.

Integrations MUST use supported native message, state, and execution contracts, preserve
successful results and state semantics, and document their actual protection boundaries.
Direct answers and answers following retrieval MUST receive applicable final-answer checks;
intermediate tool requests MUST NOT be treated as final answers. A separate demonstration
application MUST NOT become a runtime dependency or prerequisite for library adoption.

### II. Privacy Before External Processing

Local PII inspection MUST precede external evaluation of protected content, including history,
retrieval evidence, and generated answers. The default protective configuration MUST require
local PII checks. Required local PII violations or evaluation failures MUST stop affected remote
evaluation and model submission; output failures MUST stop remote output evaluation and delivery.
Explicitly optional PII checks MUST be documented as monitoring with reduced protection.

Supported integrations MUST inspect assembled model input after context additions. They MUST NOT
describe entry-only checks as complete input protection. Unsupported content forms, missing
configured capabilities, and invalid policies MUST fail explicitly rather than bypass protection.
Routine records and exceptions MUST exclude raw content, detected PII values, and credentials.
Evaluation state MUST remain isolated between requests. Protection mechanisms must not become
an additional disclosure path.

### III. Explicit and Consistent Enforcement

Live enforcement, offline evaluation, and framework adapters MUST share policy definitions and
decision rules. Each check MUST distinguish pass, violation, inconclusive, evaluation error,
and skipped outcomes. Applicable required violations, inconclusive judgments, and evaluation
errors MUST block through distinguishable exceptions. Optional outcomes MUST be recorded and
MUST NOT override required failures.

Groundedness MUST use identifiable evidence associated with answer generation. Missing evidence
MUST be recorded as skipped, never passed; it MUST block when evidence is separately required.
Unavailable required decision information MUST NOT be treated as a pass. Invalid configuration
MUST NOT silently disable protection. Cancellation and caller exceptions MUST be preserved.
Allowed results MUST retain their native form without silent rewriting, regeneration, or model
switching. Documentation MUST distinguish blocking delivery from reversing earlier tool actions,
model costs, or application persistence; the library MUST NOT claim such rollback.

### IV. Independent Oracles and Test-Driven Development

For behavioral changes, contributors MUST establish expected outcomes from the specification,
documented external contracts, manually reasoned examples, independently calculated results,
or independently reviewed labels before executing the implementation for those cases.
Contributors MUST NOT run an implementation to discover behavior and then adopt its outputs as
test expectations, snapshots, golden files, labels, or expected call sequences. Production
parsers, reducers, and metric functions MUST NOT calculate their own expected test results.

Each behavioral task MUST retain a test-design record with requirement references, fixture
rationale, expected outcomes, prohibited side effects, and oracle provenance. Tests MUST first
demonstrate an intended behavioral failure, then pass after implementation, followed by
refactoring with expectations fixed. Import or environment failures alone do not establish a
behavioral failure. Assertions, labels, and thresholds MUST NOT be weakened to fit observed
results; corrections MUST cite independent authority or a documented specification amendment.

Deterministic tests MUST require neither API keys nor external network access. Framework
integration tests MUST exercise real framework contracts with controlled inference and transport.
Passing mocks alone does not demonstrate a working integration. Unresolved expected behavior
MUST be recorded and resolved before claiming a task complete.

### V. Honest Evaluation and Safe Observability

Reports MUST separate policy violations, evaluation errors, inconclusive outcomes, and skips.
Correctness claims MUST use independent reference labels, identify denominators, and disclose
false alarms, missed violations, and unclassified cases. Without labels, reports MUST NOT claim
accuracy. Software correctness, detector quality, and model judgment quality MUST be reported
separately. Groundedness MUST NOT be presented as proof that supplied evidence is true.

Policy rubrics, reference labels, and quality acceptance criteria MUST be fixed before the
evaluation run they assess. Calibration MUST use development data; held-out labels MUST NOT be
changed to obtain a passing result. Evaluation evidence MUST identify relevant code, policy,
model, detector, framework, and dataset versions.

Operational records MUST include the check, boundary, outcome, available confidence, elapsed
time, policy identity, available evaluator version, and error category. Usage and cost MUST be
reported when available; unavailable values MUST remain absent or explicitly unknown, never
invented as zero. Published claims MUST disclose measured coverage, overhead, and detection
limits rather than promise universal protection.

## Open Source and Compatibility

- Public releases MUST include an explicit open source license, package metadata, installation
  instructions, contribution guidance, and working examples. Dependency and bundled asset
  licenses MUST be reviewed for compatibility before distribution; this constitution does not
  select a license on the maintainers' behalf.
- Public APIs, policy defaults, failure modes, supported content forms, and compatibility ranges
  MUST be documented. Claimed dependency ranges MUST have compatibility evidence, including
  tests of their oldest and newest claimed versions.
- Library releases MUST use semantic versioning and explain compatibility changes in release
  notes. Breaking APIs, policy defaults, or enforcement behavior MUST be identified explicitly
  with migration guidance; they MUST NOT be hidden in a patch release.
- The current v1 baseline includes LangChain, LangGraph, and Microsoft Agent Framework Python
  integrations, synchronous and asynchronous non-streaming use where supported, and shared live
  and offline evaluation. OpenRouter/Jev is the initial judgment provider; the protected
  application's answer provider remains independent.
- Streaming, general HTTP interception, independent tool authorization, automated answer repair,
  hosted dashboards, and the separate RAG application remain outside the current release scope.
  Scope changes MUST first amend the product specification and affected acceptance cases.
- Technical choices, exact dependency versions, detector coverage, and calibrated thresholds
  MUST be recorded and validated in implementation decision records. New dependencies and
  abstractions MUST be justified by a concrete requirement before adoption.

## Development Workflow and Release Gates

The workflow MUST proceed from requirements to verified contracts, independent test design,
failing behavioral tests, implementation, refactoring, and release evidence. The behavioral
baseline is `agent-guard-spec.md`; technical planning is recorded in
`agent-guard-implementation-plan.md`. Requirement and acceptance identifiers MUST remain
traceable through tasks, tests, and release evidence.

Contributors, including coding agents, MUST keep tasks bounded and document routine engineering
decisions. They MUST NOT redefine product behavior to accommodate implementation results.
Conflicting requirements MUST be resolved through a recorded specification decision before
dependent expectations or production behavior are changed.

Every pull request MUST be reviewed for constitutional compliance, independent test provenance,
privacy boundaries, compatibility, and unsupported claims. Relevant formatting, static and type
checks, packaging checks, deterministic tests, and impacted integration tests MUST pass.
Documentation-only changes MUST receive document validation without requiring unrelated tests.
Behavioral changes MUST update affected documentation and traceability.

A release MUST demonstrate all applicable acceptance cases across every promised integration,
successful installation of advertised dependency groups, and explicit failure when a configured
required capability is unavailable. Provider smoke tests and labeled quality evaluations MUST
be explicitly enabled, use predeclared expectations, and remain separate from deterministic
tests. Releases MUST publish measured limitations and overhead. A failed quality gate requires
diagnosis or a documented specification revision, never relabeling held-out data to pass.

## Governance

This constitution governs project specifications, plans, implementation, and reviews. Product
specifications define observable behavior within these principles; technical plans define how
to implement it. Conflicts MUST be surfaced and resolved explicitly, never silently bypassed.

Amendments MUST document proposed wording, rationale, affected principles, compatibility impact,
and migration or follow-up work. A project maintainer MUST review and accept amendments before
merge. Accepted amendments MUST update the version and last-amended date while preserving the
original ratification date. Initial ratification is this adoption on 2026-09-23.

Constitution versions use semantic versioning: MAJOR for incompatible principle removals or
redefinitions, MINOR for new principles or materially expanded guidance, and PATCH for
clarifications without changed obligations. Version 1.0.0 replaces an unratified scaffold with
the first project-specific governance baseline. Constitution and library versions are independent.

Plans, pull requests, and release reviews MUST record compliance or identify unresolved conflicts.
Exceptions MUST be explicit, maintainer-approved, bounded in scope and duration, and include
corrective work; permanent incompatible exceptions require a constitutional amendment.
The temporary Sync Impact Report MUST be removed before the amended document is committed.

**Version**: 1.0.0 | **Ratified**: 2026-09-23 | **Last Amended**: 2026-09-23
