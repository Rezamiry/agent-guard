"""Sanitized operational records."""

from .models import CheckResult, _valid_identity


def record_for(result: CheckResult, *, policy_id: str, settings_id: str | None = None,
               content: str = "", credential: str = "") -> dict[str, object]:
    if not _valid_identity(policy_id):
        raise ValueError("invalid_policy_identity")
    if settings_id is not None and not _valid_identity(settings_id):
        raise ValueError("invalid_settings_identity")
    return {
        "check": result.check_id,
        "boundary": result.boundary.value,
        "outcome": result.outcome.value,
        "policy": policy_id,
        "settings_id": settings_id,
        "reason_code": result.reason_code,
        "confidence": result.confidence,
        "elapsed_seconds": result.elapsed_seconds,
        "evaluator": result.evaluator,
        "error_category": result.error_category,
        "cost": result.cost,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
