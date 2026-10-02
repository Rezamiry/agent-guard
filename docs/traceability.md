# Requirement Traceability

Source of truth: `specs/001-agent-guard/spec.md`, especially its Acceptance Traceability
table. Every FR-01–FR-34 and AC-01–AC-34 appears below. The fixture expectations and
prohibited side effects come from `docs/testing/oracles.md`, which was written independently
of the implementation. A listed test is controlled local evidence, not a release claim.

| Requirements | Acceptance scenarios | Independent oracle / controlled test files | Supported surfaces and remaining evidence |
| --- | --- | --- | --- |
| FR-01, FR-02 | AC-01, AC-12, AC-23 | US4 native boundary and US5 parity oracles; `tests/integration/test_langchain.py`, `test_langgraph.py`, `test_microsoft.py`, `tests/acceptance/test_offline.py` | Core, LangChain invoke/ainvoke, LangGraph invoke/ainvoke, Microsoft async; full native parity, compatibility and license gates open |
| FR-03, FR-07, FR-08, FR-10 | AC-02, AC-03, AC-05, AC-15, AC-16, AC-27, AC-28 | US1 input, input early-stop and explicit-request oracles; `tests/privacy/test_input_boundary.py`, `test_core_boundaries.py`, `tests/unit/test_policy_authoring.py`, `tests/contracts/test_local_pii.py` | Core and selected native paths; complete provider-added and later-mutator matrix open |
| FR-04, FR-09 | AC-04, AC-06, AC-07, AC-27 | US2 final-answer and output privacy oracles; `tests/acceptance/test_core_output.py`, `tests/privacy/test_output_boundary.py`, `tests/unit/test_semantic_checks.py` | Core and selected native final hooks; full native final-path matrix open |
| FR-05, FR-06 | AC-11, AC-20 | US2 and US4 native oracles; `tests/acceptance/test_core_output.py`, `tests/integration/test_langchain.py`, `test_langgraph.py`, `test_microsoft.py` | Ordinary/async where promised; full direct/retrieval and cancellation matrix open |
| FR-11, FR-12, FR-13 | AC-06, AC-07, AC-08, AC-17 | Independent-evidence and shared-rubric oracles; `tests/unit/test_semantic_checks.py`, `test_semantic_rubrics.py`, `tests/acceptance/test_core_output.py` | Core controlled judgments; held-out semantic quality open |
| FR-14, FR-15, FR-16, FR-17, FR-18 | AC-08, AC-09, AC-10, AC-16, AC-18, AC-30, AC-31 | Decision, US3 fault and deadline oracles; `tests/unit/test_decisions.py`, `test_failure_taxonomy.py`, `tests/contracts/test_jev_failures.py`, `test_jev_provider.py` | Core/provider controlled transport; live smoke and complete native fault matrix open |
| FR-19 | AC-14, AC-15, AC-22, AC-29, AC-30 | US3 setup/fault and size oracles; `tests/unit/test_guard_lifecycle.py`, `test_input_snapshots.py`, `tests/privacy/test_piece_boundaries.py`, `tests/contracts/test_native_adapters.py` | Core, selected native rejection paths; dependency-range endpoints open |
| FR-20, FR-21, FR-22, FR-23 | AC-12, AC-13, AC-24, AC-25 | US5 saved-data, parity, metrics and report oracles; `tests/contracts/test_dataset_jsonl.py`, `tests/acceptance/test_offline.py`, `tests/acceptance/test_cross_framework_parity.py`, `tests/unit/test_metrics.py`, `tests/privacy/test_report_export.py` | Offline controlled examples and cross-framework decision parity (core, LangChain, LangGraph, Microsoft, offline) now covered; independent held-out labels still open |
| FR-24, FR-27 | AC-02, AC-04, AC-19, AC-26 | Sanitized-record and US5 report oracles; `tests/privacy/test_sanitized_records.py`, `test_report_export.py`, `tests/unit/test_policy_authoring.py` | Core/offline records; measured quality, usage and cost open |
| FR-25, FR-26 | AC-20, AC-21, AC-22 | US3 and US4 isolation/fault oracles; `tests/unit/test_failure_taxonomy.py`, `test_input_snapshots.py`, `tests/contracts/test_native_adapters.py` | Controlled cancellation, limits and streaming rejection; concurrent native matrix open |
| FR-28, FR-29 | AC-23, AC-26 | US1 detector and US5 quality oracles; `tests/contracts/test_local_pii.py`, `test_package_imports.py`, `tests/integration/test_langchain.py`, `test_langgraph.py`, `test_microsoft.py` | Local preset and pinned-framework examples; labeled quality, package-range and license acceptance open |
| FR-30 | AC-29, AC-31 | Provider total-deadline oracle; `tests/contracts/test_jev_failures.py` | Controlled transport only; live provider smoke open |
| FR-31 | AC-32 | US4 native boundary oracle; `tests/integration/test_langchain.py`, `test_langgraph.py`, `test_microsoft.py` | Selected real-framework paths; complete direct/retrieval surface matrix open |
| FR-32 | AC-33 | US1 changed-snapshot and US4 native boundary oracles; `tests/privacy/test_input_boundary.py`, `tests/integration/test_langgraph.py`, `test_microsoft.py` | Observable changed inputs rechecked; privately assembled LangGraph prompt and later-mutator matrix open |
| FR-33, FR-34 | AC-34 | Input limits and adapter-fault oracles; `tests/unit/test_input_snapshots.py`, `test_failure_taxonomy.py`, `tests/contracts/test_native_adapters.py` | Core and selected native forms/faults; complete native content and fault matrix open |

Release evidence and remaining gates are recorded in `docs/release-evidence.md`. The
independent development and held-out datasets and a live Jev credential were reported
unavailable on 2026-09-28, so AC-26 and live-provider claims remain open.
