# Contributing to Agent Guard

Thanks for your interest. Agent Guard is released under the [Apache License 2.0](LICENSE); by
contributing you agree your contribution is licensed the same way.

Do not copy the separately provisioned spaCy PII model into this repository or a distribution.
Package publishing is not set up yet; the release gates are tracked in
[`docs/release-evidence.md`](docs/release-evidence.md).

## Setup

```bash
uv venv .venv --python 3.12
uv sync --locked --python .venv/bin/python --all-extras --group dev
uv pip install --python .venv/bin/python \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

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
