# Validation Quickstart: Agent Guard Python SDK

This guide tracks end-to-end validation. The SDK package, deterministic tests, and lockfile
exist; release gates remain open. Behavioral expectations come from [spec.md](spec.md) and the
[contracts](contracts/), not from observed SDK output.

## Prerequisites

- Linux x86-64 with Python 3.11 and 3.12 for the advertised initial matrix, plus `uv`.
- The committed lockfile and separately installed English PII model described in [research.md](research.md).
- No provider key or network for deterministic checks. Enable provider smoke and quality runs separately with explicit credentials and predeclared fixtures.
- An accepted open source license, third-party notice review, and documented compatibility ranges before a public release.

## Install and validate packages

Create a project-local environment and exercise each optional installation group independently.
Run all Python tools through `.venv/bin/python` or `uv run` so no packages are installed on system
Python. The intended release validation commands are:

```bash
uv sync --locked --group dev --extra pii
uv run pytest -q tests/unit tests/privacy tests/contracts
uv sync --locked --group dev --extra pii --extra jev --extra langchain --extra langgraph --extra microsoft
uv run pytest -q tests/integration tests/acceptance
uv run ruff check .
uv run mypy src/agent_guard
uv build
```

The implementation phase must confirm exact `uv` group/extra names against `pyproject.toml`. Passing the combined install is insufficient by itself: base import and each advertised extra must install independently, and oldest/newest versions of every claimed dependency range need compatibility evidence. No framework is a required base-package dependency.

## Behavioral journeys

| Journey | Expected result | Requirement evidence |
| --- | --- | --- |
| Default input and output checks on supported text | Required local PII only; safe native result unchanged; no external evaluator call. | AC-01, AC-28, FR-08 |
| PII in initial or later assembled input | No affected model or external evaluator submission; sanitized exception. | AC-02, AC-03, AC-33 |
| PII in final answer or output-evaluation context | No remote output evaluation or final delivery. Earlier model cost and tool effects are not reversed. | AC-04, AC-34 |
| Direct and retrieval answers in each supported integration | Final checks run on both paths; intermediate tool requests are not final answers. | AC-11, AC-32 |
| Required versus optional semantic violation, uncertainty, and runtime error | Required blocks with distinct reasons; optional records and allows only when all required conditions permit. | AC-09, AC-10, AC-30, AC-31 |
| Absent identified evidence | Groundedness is skipped; separate evidence requirement blocks if enabled. | AC-08 |
| LangChain and LangGraph ordinary/async; Microsoft native async | Same controlled policy decision for equivalent content; allowed native result, metadata, and state preserved. | AC-01, AC-20, AC-32 |
| Changed content after an earlier check | Rechecked before model handoff, or known bypassing arrangement rejected at setup. | AC-33 |
| Exact-limit and over-limit text/messages/evidence; unsupported multimodal part | Exact limit accepted when all limits pass; over-limit or unsupported form rejected without truncation or silent omission. | AC-14, AC-34, FR-33 |
| Known incompatible arrangement versus unexpected runtime adapter fault | Configuration versus integration failure; neither is treated as optional check monitoring. | AC-22, AC-34 |
| Saved-example policy comparison | Existing answers are not regenerated; changed decisions, denominators, skips, errors, and unknown values are reported accurately. | AC-12–AC-13, AC-24–AC-25 |

Use real framework message/state objects and controlled inference/transport. Expected native results and prohibited side effects must be authored from the spec and published framework contracts before running the implementation. Provider smoke tests are separate from deterministic checks; statistical quality gates use frozen independent labels and report real limitations.

## Release review

Check all AC-01–AC-34 across their applicable integrations and surfaces. Publish the installation and safe/blocked examples for LangChain, LangGraph, and Microsoft Agent Framework Python, actual protection boundaries, supported content forms and limits, compatibility evidence, measured overhead and available cost, quality results with denominators, and known detection limits. Do not claim success for an unrun dependency/version or unsupported streaming path.
