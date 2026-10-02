# Compatibility and supported boundaries

This is an implementation status record, not a release certification. The checked local
environment is Linux x86-64, Python 3.12.14 in `.venv`.

| Component | Version checked locally | Evidence so far | Remaining gate |
| --- | --- | --- | --- |
| Python | 3.11.16 / 3.12.14 | Both: 199 passed, 0 skipped, model asset provisioned on each; Ruff and mypy pass on 3.12 | — |
| Pydantic | 2.12.5 (oldest) – 2.13.5 (newest, locked) | Full 199-test suite passed at both range endpoints | — |
| Presidio | 2.2.364 (exact pin) | Curated local recognizer category fixtures | Frozen-label quality assessment |
| spaCy / English model | 3.8.0 (oldest) – 3.8.16 (newest, locked) / 3.8.0 | Full suite passed at both spaCy range endpoints with the pinned model asset | Quality and benign near-match assessment |
| tldextract | 5.0.0 (oldest) – 5.3.2 (newest, locked) | Full 199-test suite passed at both range endpoints | — |
| LangChain / core | 1.4.2 / 1.6.4 (exact pins) | Native middleware, real ordinary/async agent, a real tool-calling loop with a tool-capable `BaseChatModel`, exact-size/multipart contracts, concurrent-request isolation, caller-exception/cancellation identity, response/usage-metadata and id preservation, and a user-middleware-placement case | Full direct/retrieval and state matrix |
| LangGraph | 1.2.12 (exact pin) | Native direct/retrieval graph, async invocation via a native async node (`AsyncGuardedModelNode`/`AsyncGuardedFinalNode`, not an executor-thread wrapper), topology rejection, concurrent-request isolation, caller-exception/cancellation identity, and extra-state-field preservation | Full reducer/state and private-assembly matrix |
| Agent Framework core | 1.19.0 (exact pin) | Native middleware, real Agent, context-provider addition, concurrent-request isolation, caller-exception/cancellation identity | Tool-cycle and full callback matrix |
| HTTPX | 0.28.0 (oldest) – 0.28.1 (newest, locked) | Full 199-test suite passed at both range endpoints; controlled one-attempt, deadline, failure, and sync portal tests | Live opt-in smoke |
| AnyIO | 4.8.0 (oldest) – 4.15.1 (newest, locked) | Full 199-test suite passed at both range endpoints | Live opt-in smoke |

Every declared runtime dependency other than the five above (`presidio-analyzer`, `langchain`,
`langchain-core`, `langgraph`, `agent-framework-core`) is an exact `==` pin, so it has no range
to test independently of the main suite. Each of the five ranged packages' oldest declared bound
was verified by overriding only that package's version in an otherwise fully-extras-installed
environment and rerunning the full deterministic suite; each was then restored to its locked
(newest) version. The base package and each of `pii`, `jev`, `langchain`, `langgraph`, and
`microsoft` install and import independently in a fresh environment; a no-extras install imports
`agent_guard` with none of the optional frameworks or detector packages present. Full detail is
in `docs/release-evidence.md`'s 2026-09-28 (T080) entry.

Cross-framework decision parity — identical controlled judgments producing identical allow/block
decisions across the core guard, LangChain, LangGraph, Microsoft, and offline evaluation for the
same content — is verified in `tests/acceptance/test_cross_framework_parity.py` (AC-12, FR-20).

The base package imports with site packages disabled. Frameworks, Presidio, and HTTPX remain
optional extras. `en_core_web_lg==3.8.0` is provisioned separately into `.venv` and is never
downloaded at detector runtime.

The checked core content forms are text messages/parts in supported roles, textual tool
descriptions, nested string keys and values in JSON-compatible tool arguments, and identified
evidence. Images, audio, video, binary attachments, opaque content, unsupported roles, and
streaming are rejected. Limits are 100,000 Unicode code points without normalization, 128
messages, 64 identified evidence items, 512 KiB outbound Jev request, and 256 KiB inbound
response. Equality with a limit is accepted when the other limits also pass.

LangChain coverage is through `create_guarded_agent(...).invoke/ainvoke`; middleware must be
registered with the input guard closest to the model and the output guard last before return.
LangGraph coverage is through declared `GuardedModelNode` and `GuardedFinalNode` paths compiled
with `compile_guarded_graph`. Microsoft coverage is through native chat and agent middleware
with a `ChatMiddlewareLayer` client; the facade rejects providers that append later middleware.
Direct access to the underlying framework object outside a facade is not covered. The current
adapters do not claim universal interception of arbitrary private prompt assembly or unknown
framework content forms.

Measured overhead, cost by category/integration, held-out quality, and broader compatibility
ranges remain pending release evidence.
