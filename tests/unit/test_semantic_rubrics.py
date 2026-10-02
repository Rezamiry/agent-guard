"""Independent semantic rubric and normalization contract."""

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Outcome
from agent_guard.checks.semantic import RUBRIC_VERSION, normalize_judgment, rubric_for


def test_versioned_relevance_and_groundedness_have_distinct_binary_criteria() -> None:
    relevance = CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT)
    grounded = CheckPolicy("grounded", CheckKind.GROUNDEDNESS, Boundary.OUTPUT)
    relevance_pass, relevance_violation = rubric_for(relevance)
    grounded_pass, grounded_violation = rubric_for(grounded)
    assert RUBRIC_VERSION == "v1"
    assert "current request" in relevance_pass
    assert "current request" in relevance_violation
    assert "identified evidence" in grounded_pass
    assert "identified evidence" in grounded_violation
    assert (relevance_pass, relevance_violation) != (grounded_pass, grounded_violation)


def test_confidence_equality_and_below_minimum_are_normalized() -> None:
    check = CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT)
    equal = CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.80)
    below = CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.79)
    assert normalize_judgment(check, equal).outcome == Outcome.PASS
    assert normalize_judgment(check, below).outcome == Outcome.INCONCLUSIVE


def test_mismatched_semantic_result_is_rejected() -> None:
    check = CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT)
    wrong = CheckResult("other", Boundary.OUTPUT, Outcome.PASS, confidence=0.95)
    with pytest.raises(ValueError):
        normalize_judgment(check, wrong)
