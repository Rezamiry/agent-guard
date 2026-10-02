# Contributing to Agent Guard

This project is preparing an open source release. The proposed project license is
Apache-2.0; maintainer acceptance and the dependency/model redistribution review are
release gates. Until those gates are recorded, do not publish a package or copy the
separately provisioned PII model into this repository or a distribution.

## Changes

1. Open an issue or describe the intended behavior and the affected native boundary.
2. Add an independent expected result to `docs/testing/oracles.md` before changing
   behavior. Include the required outcome, prohibited external calls, and source of
   the expectation.
3. Add a focused regression test, implement the change, and update the corresponding
   requirement and acceptance evidence in `docs/traceability.md`.
4. Run `python -m pytest -q`, `python -m ruff check .`, and
   `python -m mypy src/agent_guard` in the project environment.

Use synthetic examples in tests and reports. Do not add real credentials, personal
data, raw conversation logs, or provider payloads to issues, fixtures, or routine
diagnostics. Tests that need live credentials must be explicitly opt-in and separate
from deterministic tests.

The project follows the current specification and constitution in `specs/` and
`.specify/memory/`. Changes to advertised compatibility, PII coverage, or quality
claims require release evidence, not just passing controlled tests.
