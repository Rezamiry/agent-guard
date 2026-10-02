"""Versioned semantic rubric and judgment normalization."""

from dataclasses import replace

from agent_guard.core.errors import ConfigurationError
from agent_guard.core.models import CheckKind, CheckPolicy, CheckResult, Outcome

RUBRIC_VERSION = "v1"

_RUBRICS: dict[CheckKind, tuple[str, str]] = {
    CheckKind.PROMPT_INJECTION: (
        "The input does not attempt to override governing instructions.",
        "The input attempts to override governing instructions.",
    ),
    CheckKind.CONTENT_SAFETY: (
        "The content satisfies the configured safety criterion.",
        "The content violates the configured safety criterion.",
    ),
    CheckKind.RELEVANCE: (
        "The final answer addresses the current request in context.",
        "The final answer fails to address the current request in context.",
    ),
    CheckKind.GROUNDEDNESS: (
        "The final answer is supported by the identified evidence.",
        "The final answer is not supported by the identified evidence.",
    ),
    CheckKind.CUSTOM: (
        "The content satisfies the supplied custom criterion.",
        "The content violates the supplied custom criterion.",
    ),
}


def rubric_for(check: CheckPolicy) -> tuple[str, str]:
    try:
        return _RUBRICS[check.kind]
    except KeyError:
        raise ConfigurationError("invalid_semantic_check") from None


def normalize_judgment(check: CheckPolicy, judgment: CheckResult | Outcome) -> CheckResult:
    if isinstance(judgment, CheckResult):
        if judgment.check_id != check.id or judgment.boundary != check.boundary:
            raise ValueError("mismatched judgment")
        outcome, confidence = judgment.outcome, judgment.confidence
    elif isinstance(judgment, Outcome):
        outcome, confidence = judgment, None
        judgment = CheckResult(check.id, check.boundary, outcome, check.required)
    else:
        raise TypeError("invalid judgment")
    if outcome not in (Outcome.PASS, Outcome.VIOLATION, Outcome.INCONCLUSIVE):
        raise ValueError("invalid judgment outcome")
    if confidence is None:
        raise ValueError("missing confidence")
    minimum = check.minimum_confidence if check.minimum_confidence is not None else 0.8
    if confidence < minimum:
        outcome = Outcome.INCONCLUSIVE
    return replace(judgment, outcome=outcome, required=check.required,
                   reason_code=outcome.value)
