# Release notes

## 0.1.1

- Accepts dated snapshots of the requested decision model in responses (for example
  `typesafe/jev-1.13-20260917`); 0.1.0 rejected them as `provider_response_invalid`.
- Configurable decision model via `AGENT_GUARD_DECISION_MODEL`.
- Opt-in `AGENT_GUARD_TRACE_DECISIONS=1` logs each Decisions exchange (state, question,
  per-choice probabilities) to stderr as `JEV_DECISION {json}`. It writes raw content to logs;
  leave it off in production.

## 0.1.0 (superseded by 0.1.1)

This is the first proposed Agent Guard release. It adds local PII checks at input and
final-answer boundaries, optional semantic checks through a separately configured Jev
evaluator, native non-streaming adapters for LangChain, LangGraph, and Microsoft Agent
Framework Python, and offline evaluation of saved candidate answers. Allowed host results
are returned without answer rewriting.

The public API and compatibility ranges are provisional. There is no prior released
Agent Guard version requiring migration. Applications adopting this version should
explicitly place guards at every model submission and final delivery boundary described
in `docs/compatibility.md`, then run the safe and blocked quickstart examples against
their own supported framework arrangement.

Both Python versions and every advertised dependency-range endpoint now pass the full
deterministic suite (199 tests, 0 skips), each optional extra installs independently, and
local overhead for the default PII-only policy is measured and published in
`docs/release-evidence.md`. This version must still remain unreleased until independently
labeled quality evaluation, opt-in live provider smoke, and maintainer license/redistribution
acceptance are recorded there — those depend on inputs (labeled datasets, a live provider
credential, a maintainer decision) that no engineering pass in this repository can supply on
its own. No quality or latency guarantee beyond the measured local-overhead numbers is implied
by this draft.
