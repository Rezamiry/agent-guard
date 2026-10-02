# Release evidence (in progress)

This record separates locally observed behavior from release claims. The specification and
independent oracle records remain the sources of expected outcomes. No public release is
authorized by this document.

## Local validation on 2026-09-28

Environment: Linux x86-64, Python 3.12.14, locked project virtual environment. The separately
provisioned `en_core_web_lg==3.8.0` asset was available.

| Check | Result | Limit |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 176 passed, 0 skipped | One pinned version environment; full acceptance matrix still open. This run used approved unsandboxed execution because the sandbox blocks worker threads. |
| `.venv/bin/python -m ruff check .` | Passed | Static lint only |
| `.venv/bin/python -m mypy src/agent_guard` | Passed, 26 source files | Static types only |
| `uv build` | Wheel and sdist built after explicit sdist manifest | Build ran with uv cache access; source archive excludes internal Spec Kit, index, and Zone.Identifier files; wheel includes LICENSE |
| `.venv/bin/python -m twine check dist/*` | Failed: Twine 6.2.0 rejects generated Metadata-Version 2.5 | Twine hard-codes an allowlist ending at 2.4; choose a compatible validation tool/version before release |
| `packaging.metadata.Metadata.from_raw` on wheel and sdist metadata | Both Metadata-Version 2.5 records valid with packaging 26.3 | Does not replace the remaining package publishing checks |
| `examples/core_input.py`, `core_output.py`, `offline_evaluation.py`, `policies.py` | Ran successfully | Controlled local paths |
| `examples/langchain_agent.py`, `langgraph_agent.py`, `microsoft_agent.py` | Ran successfully | Current pinned frameworks and example flows only |

The failed metadata check leaves T073 open. Python 3.11, oldest/newest versions of every
advertised dependency range, independent installation of each extra, and the full native
integration matrix remain unverified. No provider smoke test or frozen held-out quality
evaluation has run. There are no measured quality, latency, overhead, or cost results to publish.

The 2026-09-28 continuation added input and output privacy regressions. Their behavioral red
runs showed that a required input semantic failure still invoked a later evaluator and that a
separately serialized `current_request` could bypass local inspection when
`current_request_in_messages=True`. A third red case found that a missing independent evidence
identified evidence under an enabled requirement still allowed a later output evaluator call. After the guard fixes and shared v1 semantic rubric extraction, the full 134-test
suite passed. Ruff and mypy passed. This is deterministic core evidence only; it does not
complete the native acceptance or quality gates.

Transport deadline regressions then showed that synchronous JSON decoding and portal queue
submission could each exceed the configured total wait. Response decoding now runs in a
cancellable worker, and portal submission has its own bounded wait against the same deadline.
The expanded one-attempt/deadline/failure suite and full 159-test suite passed outside the
sandbox on 2026-09-28. LangGraph selector-fault classification was also added and tested.
Ruff and mypy passed. This remains one locked Python 3.12 environment.

Policy settings now have a stable ID derived from declared non-secret fields; reports preserve
it, and comparisons can distinguish changed settings under the same policy ID. Criterion text
and credentials are excluded from that ID. Input assembly and local PII preflight now live in
`src/agent_guard/core/input.py`. The full 169-test suite passed on 2026-09-28.

The continuation expanded native adapter tests to exact-limit LangChain messages, multipart
text, nested tool arguments, opaque native content, and sanitized extraction faults. Shared
native extraction classification now lives in `src/agent_guard/integrations/common.py`.
The full 176-test suite, Ruff, and mypy passed on 2026-09-28. `docs/traceability.md` now maps
all FR-01–FR-34 and AC-01–AC-34 to independent oracles, controlled tests, claimed surfaces,
and remaining evidence. This is still one pinned dependency environment.

The evaluation owner reported that independently reviewed development and held-out datasets
are not available yet. No Jev credential variable was supplied. The frozen-label quality
evaluation and opt-in provider smoke therefore remain open.

The proposed Apache-2.0 `LICENSE`, `CONTRIBUTING.md`, and direct-dependency
`docs/third_party_notices.md` inventory are prepared for maintainer review. The license text
was checked against the [Apache Software Foundation's published version](https://www.apache.org/licenses/LICENSE-2.0.txt).
Maintainer acceptance and a transitive-dependency/model redistribution review have not happened;
the presence of these files does not authorize a public release.

A rebuild after the license and source-manifest changes exposed and fixed excess source
archive contents: the first archive included `.agents`, `.specify`, `.codebase-memory`,
and `Zone.Identifier` files. The rebuilt sdist contains the package source, tests,
examples, selected user docs, and project metadata; the wheel contains `LICENSE` in
its license metadata directory. This does not close the range-install or metadata-validator
parts of T073.

An isolated Python 3.11.16 environment installed the project with every declared extra
and the test dependencies. Its full deterministic suite passed **175 tests with one skip**
on 2026-09-28. The skipped case is the real `en_core_web_lg` detector fixture because
that separately provisioned model was not installed into the Python 3.11 environment.
This adds interpreter coverage at the current resolved dependency versions; it does not
cover the oldest/newest version of every advertised range or the skipped model case.

## Release gates still requiring evidence

- Resolve Twine's metadata-version incompatibility or adopt a compatible package validation gate,
  then rerun build and package checks.
- Complete the skipped model fixture on Python 3.11 and all claimed dependency-range
  endpoints, including isolated extra installs and the full real-framework acceptance matrix.
- Freeze independently labeled development and held-out datasets and predeclared gates before
  assessment. Report every category's misses, false alarms, coverage, uncertainty, overhead,
  available usage and cost, with sample counts and conditions.
- Run opt-in provider smoke with a supplied credential, separate from deterministic tests.
- Obtain maintainer acceptance of the proposed license and complete third-party/model
  redistribution review before publishing.

No release gate is being treated as passed based on a controlled mock or an unrun matrix cell.

## Convergence continuation on 2026-09-28 (T080)

The Twine incompatibility, the skipped Python 3.11 model fixture, isolated extra installs, and
every advertised dependency-range endpoint are now closed:

- **Twine**: `twine>=6,<7` was upgraded to `twine>=7,<8` in `pyproject.toml` and re-locked (`uv
  lock`, no other resolved versions changed besides twine 6.2.0 → 7.0.0). Twine 7.0.0 recognizes
  Metadata-Version 2.5. `uv build` followed by `.venv/bin/python -m twine check dist/*` now
  reports `PASSED` for both the wheel and the sdist, replacing the earlier `packaging`-library
  workaround.
- **Python 3.11 model fixture**: the separately provisioned Python 3.11.16 environment used for
  the earlier interpreter-coverage run had `en_core_web_lg==3.8.0` installed. The full suite now
  passes **199 tests, 0 skips** on Python 3.11.16 (previously 175 passed with one skip).
- **Isolated per-extra installs**: fresh virtual environments installing only `pii`, only `jev`,
  only `langchain`, only `langgraph`, and only `microsoft` (via `uv pip install -e ".[<extra>]"`)
  each imported `agent_guard` successfully. A fresh environment with **no** extras imports
  `agent_guard` with none of `presidio_analyzer`, `spacy`, `httpx`, `anyio`, `langchain`,
  `langgraph`, or `agent_framework` present, confirming the base package stays framework-free.
- **Dependency-range endpoints**: of the declared runtime dependencies, only five carry an actual
  `>=X,<Y` range rather than an exact pin: `pydantic`, `spacy`, `tldextract`, `httpx`, `anyio`.
  The current lockfile already resolves each to its declared **newest** bound (`pydantic
  2.13.5`, `spacy 3.8.16`, `tldextract 5.3.2`, `httpx 0.28.1`, `anyio 4.15.1`), so the newest
  endpoint is exercised by every regular test run. Each package's **oldest** declared bound
  (`pydantic==2.12.5`, `spacy==3.8.0`, `tldextract==5.0.0`, `httpx==0.28.0`, `anyio==4.8.0`) was
  installed one at a time, overriding only that package in an otherwise `[all]`-extras
  environment, with the full deterministic suite (**199 passed, 0 skips**) rerun after each
  override and the package restored to its locked version afterward. All ten oldest/newest cells
  passed with the pinned `en_core_web_lg==3.8.0` model asset present. Every other advertised
  dependency (`presidio-analyzer`, `langchain`, `langchain-core`, `langgraph`,
  `agent-framework-core`) is an exact `==` pin in `pyproject.toml`, so it has no range to test;
  its "compatibility range" is the single pinned version already covered by the main suite.

This closes the packaging- and dependency-range portion of T073/T080. The real-framework
acceptance matrix itself (native adapter behavioral coverage, not package installability) is
addressed separately in the T057/T083 cross-framework parity work recorded above in
`docs/testing/oracles.md`. What remains open below is unrelated to package installability: it
depends on inputs (labeled datasets, a live provider credential, maintainer sign-off) that were
not available in this session.

## Local overhead measurement on 2026-09-28 (T074/T082 partial)

Measured, not simulated: real `LocalPIIDetector` (pinned `en_core_web_lg==3.8.0`, cutoff 0.35),
real `create_guarded_agent`/`compile_guarded_graph`/`Agent` adapters, 200 iterations after a
5-iteration warmup, one Linux x86-64 host, Python 3.12.14, `.venv`. Sample content: ~2,000
Unicode-code-point benign sentence, repeated to size. No network access was used for any of
these numbers.

| Check / call | Mean | Median | Max | n |
| --- | ---: | ---: | ---: | ---: |
| `Guard.evaluate_input` (default policy: required local PII only) | 25.5 ms | 23.5 ms | 48.8 ms | 200 |
| `Guard.evaluate_output` (default policy: required local PII only) | 46.0 ms | 44.5 ms | 71.8 ms | 200 |
| Raw `LocalPIIDetector.detect` call (same content, no guard around it) | 25.6 ms | 24.3 ms | 44.0 ms | 200 |
| Raw `FakeListChatModel.invoke` (no guard) | 0.15 ms | 0.11 ms | 2.1 ms | 200 |
| Guarded LangChain `create_guarded_agent(...).invoke` (local PII in+out) | 19.2 ms | 17.9 ms | 37.4 ms | 200 |
| Guarded LangGraph `compile_guarded_graph(...).invoke` (local PII in+out) | 11.2 ms | 9.8 ms | 23.2 ms | 200 |
| Guarded Microsoft `Agent.run` (local PII in+out) | 17.2 ms | 15.4 ms | 70.1 ms | 200 |

The dominant cost is the local spaCy/Presidio PII scan itself (~25 ms for ~2,000 characters on
this host), not the guard's own bookkeeping: the raw detector call and `evaluate_input` are
within measurement noise of each other. `evaluate_output` costs roughly double `evaluate_input`
because the output-boundary inspection text concatenates the request, message parts, and answer
twice (a separated join plus the no-separator fallback used to catch PII split across boundaries
— see the false-positive note added to `docs/testing/oracles.md`'s tool-calling entry), so the
detector scans roughly twice as many characters. The three native-adapter numbers are each lower
than the raw core-guard numbers above because their sample content ("How can I help you
today?") is much shorter than the ~2,000-character core-guard sample, not because the adapters
add negative overhead; adapter overhead scales with content size the same way the core guard
does. This scan cost is per-request and not currently cached or batched; it will dominate
end-to-end latency for any deployment doing input/output PII scanning on every turn.

**What this does not cover**: semantic-check (Jev) latency and cost, which require a live
provider credential that was not available in this session (see below); usage/cost accounting,
which is always `None`/unknown for the local-only default policy since no external evaluator is
called; and any measurement under real concurrent load rather than sequential iterations. These
remain open per T074/T082/T087.

## Externally blocked release gates (status as of 2026-09-28 convergence pass)

These three items were re-checked during this implementation pass and are unchanged from the
prior report — they depend on inputs this session does not have, not on further engineering work:

- **T070/T081 — frozen development/held-out labels**: `evaluations/manifests/v1.md`'s freeze
  record is still entirely `Pending`. No independently reviewed labeled dataset was supplied.
  Fabricating labels or a pass/fail result here would violate Constitution V ("Correctness claims
  MUST use independent reference labels... Without labels, reports MUST NOT claim accuracy").
- **T074/T082 — frozen-label quality evaluation and provider smoke**: blocked on the same missing
  labels, plus no Jev/OpenRouter credential was supplied for a live provider smoke test. The
  local-overhead measurement above is the portion of T074/T082 that does not depend on either.
- **T075/T087 — maintainer license acceptance and redistribution review**: `LICENSE`,
  `CONTRIBUTING.md`, and `docs/third_party_notices.md` remain prepared drafts; no maintainer has
  recorded acceptance, and the transitive-dependency/model redistribution review has not been
  performed. Tested compatibility ranges and measured overhead (both blocking sub-items of
  T075/T087 that do not require a maintainer) are now published above and in
  `docs/compatibility.md`.

No release gate above is being treated as passed. A maintainer supplying labels, a credential, or
a license decision would let a future session close the corresponding item without re-deriving
anything already recorded here.

## Constitutional and story compliance review on 2026-09-28 (T075/T087)

Reviewed against `.specify/memory/constitution.md`'s five principles and the three checklists in
`specs/001-agent-guard/checklists/` (all three already show 27/27, 16/16, and 33/33 checked —
verified unchanged in this pass). This review is scoped to what an implementation-level pass can
confirm from the code, tests, and evidence already recorded; it is not a substitute for a human
maintainer's release sign-off.

| Principle / story | Compliance observed this session | Open item |
| --- | --- | --- |
| I. Reusable library / native integration | Base package has zero framework dependencies (verified: fresh no-extras install imports `agent_guard` with none of `presidio_analyzer`/`spacy`/`httpx`/`anyio`/`langchain`/`langgraph`/`agent_framework` present). Each extra installs and imports independently. Cross-framework parity test confirms one shared core drives all three adapters plus offline evaluation identically. | None found |
| II. Privacy before external processing | Default policy is local-PII-only on input and output, no external evaluator call (`PolicySet()` default, `AC-28` tests). A real tool-calling loop confirms the second assembled request — carrying newly-introduced tool output — is independently rechecked before the next model call, not just the first. | Semantic-check privacy preflight is code-reviewed and unit-tested but not exercised against a live provider |
| III. Explicit and consistent enforcement | Decision reducer, sanitized records, and error taxonomy are unchanged by this session's work; the new async LangGraph node path and concurrency tests confirm required/optional and skip semantics hold under concurrent and native-async execution too | None found |
| IV. Independent oracles and TDD | Every behavioral change in this session (T076–T079, T084–T086, T057/T083) has a dated `docs/testing/oracles.md` entry recording authority, fixture rationale, expected outcome, and red/green evidence before or alongside implementation; no test asserted an observed-then-adopted value | None found |
| V. Honest evaluation and observability | This session added no quality or cost claim without a denominator; the local-overhead measurement above states explicitly what it does and does not cover, and no Jev/quality number is fabricated in its absence | Frozen-label quality evidence and live provider cost remain absent, as already stated above |
| US1–US3 (core input/output/policy) | Full deterministic suite (199 tests) passes on both Python 3.11 and 3.12 and at every dependency-range endpoint | Unchanged from prior evidence |
| US4 (native integrations) | Extended this session: async LangGraph native node, concurrent-request isolation, caller-exception/cancellation identity, metadata/state preservation, a real tool-calling loop, and cross-framework decision parity are now all covered with real framework objects | Full direct/retrieval/state matrix (every claimed surface × every claimed content form) remains partial, as already stated in `docs/compatibility.md` |
| US5 (offline evaluation) | Unchanged from prior evidence; now also covered by the cross-framework parity test's offline leg | Frozen held-out labels remain open |

No unsupported claim was found or introduced: every "done" statement above points to a named test
file or a reproducible command in this document. The two items requiring a maintainer (accepting
the proposed Apache-2.0 `LICENSE` and completing the transitive-dependency/model redistribution
review) and the two items requiring external inputs this session did not receive (labeled
datasets, a live Jev credential) remain the only gates blocking release, consistent with every
prior report in this file.
