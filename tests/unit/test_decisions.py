import pytest

from agent_guard import Boundary, CheckResult, Outcome
from agent_guard.core.decision import reduce_results


def test_optional_error_does_not_block() -> None:
    result = CheckResult("optional", Boundary.OUTPUT, Outcome.EVALUATION_ERROR, False, "timeout")
    assert reduce_results((result,)).allowed is True


def test_required_inconclusive_and_violation_block_with_distinct_reasons() -> None:
    violation = CheckResult("a", Boundary.INPUT, Outcome.VIOLATION, True, "pii_found")
    uncertain = CheckResult("b", Boundary.INPUT, Outcome.INCONCLUSIVE, True, "low_confidence")
    assert reduce_results((violation,)).reason_code == "pii_found"
    assert reduce_results((uncertain,)).reason_code == "low_confidence"


def test_skipped_evidence_without_requirement_is_not_pass() -> None:
    result = CheckResult("grounded", Boundary.OUTPUT, Outcome.SKIPPED, True, "no_evidence")
    decision = reduce_results((result,), evidence_present=False)
    assert decision.allowed is True
    assert decision.results[0].outcome == Outcome.SKIPPED


@pytest.mark.parametrize(
    ("outcome", "required", "allowed"),
    [
        (Outcome.PASS, True, True), (Outcome.PASS, False, True),
        (Outcome.VIOLATION, True, False), (Outcome.VIOLATION, False, True),
        (Outcome.INCONCLUSIVE, True, False), (Outcome.INCONCLUSIVE, False, True),
        (Outcome.EVALUATION_ERROR, True, False), (Outcome.EVALUATION_ERROR, False, True),
        (Outcome.SKIPPED, True, True), (Outcome.SKIPPED, False, True),
    ],
)
def test_spec_decision_table(outcome: Outcome, required: bool, allowed: bool) -> None:
    result = CheckResult("check", Boundary.OUTPUT, outcome, required)
    decision = reduce_results((result,))
    assert decision.allowed is allowed
    assert decision.results == (result,)


def test_optional_pass_cannot_override_required_error_and_absent_evidence_blocks() -> None:
    error = CheckResult("required", Boundary.OUTPUT, Outcome.EVALUATION_ERROR, True)
    optional = CheckResult("optional", Boundary.OUTPUT, Outcome.PASS, False)
    assert not reduce_results((error, optional)).allowed
    skipped = CheckResult("grounded", Boundary.OUTPUT, Outcome.SKIPPED, True)
    decision = reduce_results((skipped,), evidence_required=True, evidence_present=False)
    assert not decision.allowed
    assert decision.reason_code == "evidence_required"
    assert decision.results[0].outcome == Outcome.SKIPPED
