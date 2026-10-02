import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Outcome, PolicySet
from agent_guard.core.models import BoundaryDecision, EvaluationContext, EvidenceItem


def test_duplicate_check_identity_is_invalid() -> None:
    first = CheckPolicy("same", CheckKind.PII, Boundary.INPUT)
    second = CheckPolicy("same", CheckKind.PII, Boundary.OUTPUT)
    with pytest.raises(ValueError):
        PolicySet(checks=(first, second))


def test_default_is_required_local_pii_only_on_both_boundaries() -> None:
    policy = PolicySet()
    assert {(check.kind, check.boundary, check.required) for check in policy.checks} == {
        (CheckKind.PII, Boundary.INPUT, True),
        (CheckKind.PII, Boundary.OUTPUT, True),
    }


def test_check_scope_validation() -> None:
    for kind, boundary in ((CheckKind.RELEVANCE, Boundary.INPUT),
                           (CheckKind.GROUNDEDNESS, Boundary.INPUT),
                           (CheckKind.PROMPT_INJECTION, Boundary.OUTPUT)):
        with pytest.raises(ValueError):
            CheckPolicy("wrong", kind, boundary)
    assert CheckPolicy("safety", CheckKind.CONTENT_SAFETY, Boundary.INPUT)
    assert CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT, criteria="No offers")


def test_confidence_range_is_inclusive_for_semantic_checks() -> None:
    for confidence in (0.0, 1.0):
        assert CheckPolicy("rel", CheckKind.RELEVANCE, Boundary.OUTPUT,
                           minimum_confidence=confidence).minimum_confidence == confidence


def test_remote_output_check_requires_local_output_pii() -> None:
    checks = (
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    )
    with pytest.raises(ValueError):
        PolicySet(checks=checks)


def test_semantic_confidence_must_be_finite_probability() -> None:
    with pytest.raises(ValueError):
        CheckPolicy("rel", CheckKind.RELEVANCE, Boundary.OUTPUT, minimum_confidence=float("nan"))
    with pytest.raises(ValueError):
        CheckPolicy("rel", CheckKind.RELEVANCE, Boundary.OUTPUT, minimum_confidence=1.1)


def test_policy_identity_cannot_contain_content() -> None:
    with pytest.raises(ValueError):
        PolicySet(id="secret@example.com")


def test_policy_rejects_unknown_kind_numeric_required_and_mutable_checks() -> None:
    with pytest.raises(ValueError):
        CheckPolicy("unknown", "unknown", Boundary.INPUT)
    with pytest.raises(ValueError):
        CheckPolicy("numeric", CheckKind.PII, Boundary.INPUT, required=1)
    with pytest.raises(ValueError):
        PolicySet(checks=list(PolicySet().checks))


def test_context_and_evidence_ids_cannot_hold_content() -> None:
    with pytest.raises(ValueError):
        EvaluationContext("secret@example.com", "hello")
    with pytest.raises(ValueError):
        EvidenceItem("secret@example.com", "safe text", "generation-1")
    with pytest.raises(ValueError):
        EvidenceItem("safe", "safe text", "secret@example.com")
    assert EvidenceItem("safe", "safe text", "generation-1").id == "safe"


def test_result_and_decision_reject_unrecognized_status_or_scope() -> None:
    with pytest.raises(ValueError):
        CheckResult("pii", "unknown", Outcome.PASS)
    with pytest.raises(ValueError):
        CheckResult("pii", Boundary.INPUT, "unknown")
    with pytest.raises(ValueError):
        CheckResult("pii", Boundary.INPUT, Outcome.PASS, required="yes")
    with pytest.raises(ValueError):
        BoundaryDecision("yes", ())
    with pytest.raises(ValueError):
        BoundaryDecision(True, ("not-a-check",))
