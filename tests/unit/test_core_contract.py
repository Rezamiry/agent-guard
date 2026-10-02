"""Independent small oracles for the shared decision and content contract."""

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Outcome, PolicySet
from agent_guard.core.content import argument_text, validate_limits
from agent_guard.core.decision import reduce_results
from agent_guard.core.errors import IntegrationError


def test_default_policy_has_required_local_pii_on_both_boundaries() -> None:
    expected = {(CheckKind.PII, Boundary.INPUT, True), (CheckKind.PII, Boundary.OUTPUT, True)}
    actual = {(item.kind, item.boundary, item.required) for item in PolicySet().checks}
    assert actual == expected


def test_optional_violation_cannot_override_required_failure() -> None:
    cases = (
        CheckResult("required", Boundary.INPUT, Outcome.EVALUATION_ERROR, True, "timeout"),
        CheckResult("optional", Boundary.INPUT, Outcome.PASS, False, "pass"),
    )
    decision = reduce_results(cases)
    assert decision.allowed is False
    assert decision.reason_code == "timeout"


def test_missing_evidence_blocks_when_independently_required() -> None:
    skipped = (CheckResult("grounded", Boundary.OUTPUT, Outcome.SKIPPED, True, "no_evidence"),)
    assert reduce_results(skipped, evidence_required=True, evidence_present=False).allowed is False
    assert reduce_results(skipped, evidence_required=False, evidence_present=False).allowed is True


def test_argument_keys_are_inspected_without_losing_structure() -> None:
    assert argument_text({"secret@example.com": {"nested": "value"}}) == (
        "secret@example.com", "nested", "value"
    )


def test_unicode_limit_counts_code_points_without_normalization() -> None:
    validate_limits(text="e\u0301" * 50_000)
    with pytest.raises(IntegrationError):
        validate_limits(text="e\u0301" * 50_000 + "a")


def test_invalid_policy_boundary_is_rejected() -> None:
    with pytest.raises(ValueError):
        CheckPolicy("relevance-input", CheckKind.RELEVANCE, Boundary.INPUT)
