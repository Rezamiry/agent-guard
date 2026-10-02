# Agent Guard

Agent Guard is an in-development Python SDK for local PII inspection and configurable agent
input/output policy decisions. The v1 behavior and limits are defined in
`specs/001-agent-guard/spec.md`; the current package is not ready for production use.

Use the project virtual environment for development:

```bash
uv venv .venv --python 3.12
uv sync --locked --python .venv/bin/python --all-extras --group dev
.venv/bin/python -m pytest -q
```

The required `en_core_web_lg==3.8.0` detector model is a separate asset. Provision it into
`.venv` before preparing `LocalPIIDetector`:

```bash
uv pip install --python .venv/bin/python \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

The detector never downloads that asset at runtime. Semantic checks are disabled by default.
Enabling one requires an evaluator; making PII optional permits processing after a local finding
and therefore reduces privacy protection. Full compatibility evidence and an accepted license
remain release tasks.

## Local examples

After provisioning the PII model, run the safe and blocked input example, final-answer
example, policy-monitoring example, and fixed saved-answer example:

```bash
.venv/bin/python examples/core_input.py
.venv/bin/python examples/core_output.py
.venv/bin/python examples/policies.py
.venv/bin/python examples/offline_evaluation.py
```

The default policy enables required local PII at input and output, with no external judgment.
Required violations, inconclusive judgments, and evaluation errors block. Optional checks
record those outcomes and continue when every required check permits. An optional PII finding
can therefore allow the protected application to submit the same content; use it only when that
reduced protection is intended. Invalid setup fails before protected work even for an optional
check. Explicitly disabled checks (`enabled=False`) do not require or prepare their detector or
evaluator; enabled checks still require their configured prerequisites. A blocked final answer
is withheld, but earlier model cost and tool effects are not
reversed.

`PolicySet.settings_id` identifies the declared non-secret settings in operational and saved
evaluation records. It includes check order, required/optional status, confidence settings,
the shared semantic rubric version, and each check's `criteria_revision`. It excludes raw
custom criterion text and credentials. When changing custom criterion wording, set a new
non-secret `criteria_revision` so comparisons can distinguish the settings without disclosing
the wording.

Saved evaluation reads versioned UTF-8 JSONL with a supplied candidate answer; it does not
generate a replacement. The example exports content-free JSON results and a CSV summary.
Accuracy, precision, recall, and false-positive rate use only classified examples with
independent labels; the CSV includes their denominators. Errors, inconclusive judgments, and
skips are counted separately. If a ratio has no denominator, it is unknown rather than zero.
Without labels, correctness is unknown. Enabling semantic checks in a saved run can still make
opt-in provider requests, subject to local PII preflight.

The current native examples are `examples/langchain_agent.py`, `examples/langgraph_agent.py`,
and `examples/microsoft_agent.py`. Their checked boundaries and unsupported arrangements are
listed in `docs/compatibility.md`.
