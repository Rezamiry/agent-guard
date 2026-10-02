"""Request-local input snapshot and local privacy preflight."""

from collections.abc import Mapping
from typing import Protocol

from .content import extract_snapshot, validate_limits
from .models import CheckPolicy, CheckResult, EvaluationContext, Outcome


class Detector(Protocol):
    def detect(self, text: str) -> bool: ...


def request_already_counted(context: EvaluationContext) -> bool:
    """Recognize the explicit request only when it exactly matches the last user message."""
    if not context.current_request_in_messages:
        return False
    for message in reversed(context.messages):
        if isinstance(message, Mapping) and message.get("role") == "user":
            return "".join(extract_snapshot((message,))) == context.current_request
    return False


def assembled_input_text(context: EvaluationContext, checks: tuple[CheckPolicy, ...]) -> str:
    """Inspect every field that may reach a model or an input evaluator."""
    validate_limits(messages=len(context.messages), evidence_items=len(context.evidence))
    parts = extract_snapshot(
        context.messages,
        evidence=tuple(item.text for item in context.evidence),
        tool_descriptions=context.tool_descriptions,
        tool_arguments=context.tool_arguments,
    )
    inspection_parts = (
        (context.current_request,) + parts
        + tuple(check.criteria for check in checks if check.criteria is not None)
    )
    counted_parts = parts + tuple(check.criteria for check in checks if check.criteria is not None)
    if not request_already_counted(context):
        counted_parts = (context.current_request,) + counted_parts
    validate_limits(text="".join(counted_parts), messages=len(context.messages),
                    evidence_items=len(context.evidence))
    if len(inspection_parts) <= 1:
        return inspection_parts[0] if inspection_parts else ""
    return "\n".join(inspection_parts) + "\n" + "".join(inspection_parts)


def local_pii_preflight(check: CheckPolicy, text: str, detector: Detector) -> CheckResult:
    """Convert local detector findings/errors into sanitized check results."""
    try:
        finding = detector.detect(text)
        if not isinstance(finding, bool):
            raise TypeError("detector returned invalid outcome")
    except Exception:  # noqa: BLE001 - detector internals may contain sensitive text
        return CheckResult(check.id, check.boundary, Outcome.EVALUATION_ERROR,
                           check.required, "detector_error", error_category="detector_error")
    return CheckResult(check.id, check.boundary,
                       Outcome.VIOLATION if finding else Outcome.PASS,
                       check.required, "pii_found" if finding else "pass")
