"""Controlled final-answer acceptance cases with fixed judgments."""

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.core.errors import InconclusiveError, PolicyViolationError
from agent_guard.core.models import EvaluationContext, EvidenceItem


class SafeDetector:
    def detect(self, text: str) -> bool:
        return False


class FixedEvaluator:
    def __init__(self, outcomes: dict[str, Outcome]) -> None:
        self.outcomes = outcomes
        self.evidence_ids: list[tuple[str, ...]] = []

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        self.evidence_ids.append(tuple(item.id for item in context.evidence))
        return CheckResult(check.id, check.boundary, self.outcomes[check.id], confidence=0.95)


def test_required_relevance_violation_blocks_final_delivery() -> None:
    evaluator = FixedEvaluator({"relevance": Outcome.VIOLATION})
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("direct", "What is 2 + 2?", candidate_answer="It is raining.")
    with pytest.raises(PolicyViolationError):
        guard.enforce_output(context)


def test_groundedness_uses_only_current_generation_and_blocks_violation() -> None:
    evaluator = FixedEvaluator({"grounded": Outcome.VIOLATION})
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("grounded", CheckKind.GROUNDEDNESS, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("retrieved", "Summarize", candidate_answer="Unsupported claim",
                                evidence=(
                                    EvidenceItem("old", "Old context", "old-generation"),
                                    EvidenceItem("current", "Current context", "this-generation"),
                                ), generation_id="this-generation")
    with pytest.raises(PolicyViolationError):
        guard.enforce_output(context)
    assert evaluator.evidence_ids == [("current",)]


def test_missing_evidence_skips_groundedness_and_separate_requirement_blocks() -> None:
    evaluator = FixedEvaluator({"grounded": Outcome.PASS})
    checks = PolicySet().checks + (CheckPolicy("grounded", CheckKind.GROUNDEDNESS,
                                               Boundary.OUTPUT),)
    context = EvaluationContext("direct", "Explain", candidate_answer="A relevant clarification.")
    optional_evidence = Guard(PolicySet(checks=checks), detector=SafeDetector(),
                              evaluator=evaluator).prepare()
    decision = optional_evidence.evaluate_output(context)
    assert decision.allowed
    assert decision.results[-1].outcome == Outcome.SKIPPED
    assert evaluator.evidence_ids == []
    required_evidence = Guard(PolicySet(checks=checks, evidence_required=True),
                              detector=SafeDetector(), evaluator=evaluator).prepare()
    with pytest.raises(InconclusiveError):
        required_evidence.enforce_output(context)
    assert evaluator.evidence_ids == []


@pytest.mark.parametrize("with_evidence", [False, True])
def test_direct_and_retrieval_final_answers_keep_the_original_candidate(with_evidence: bool) -> None:
    evaluator = FixedEvaluator({"relevance": Outcome.PASS})
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    evidence = (EvidenceItem("source", "Known fact", "gen"),) if with_evidence else ()
    candidate = "I can clarify that answer."
    context = EvaluationContext("answer", "What happened?", candidate_answer=candidate,
                                evidence=evidence, generation_id="gen")
    assert guard.enforce_output(context) is candidate
    assert evaluator.evidence_ids == [("source",) if with_evidence else ()]


@pytest.mark.parametrize("kind", [CheckKind.CONTENT_SAFETY, CheckKind.CUSTOM])
@pytest.mark.parametrize("required", [False, True])
def test_safety_and_custom_criteria_follow_required_optional_decisions(
    kind: CheckKind, required: bool,
) -> None:
    evaluator = FixedEvaluator({"criterion": Outcome.VIOLATION})
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("criterion", kind, Boundary.OUTPUT, required=required,
                    criteria="Use approved language." if kind == CheckKind.CUSTOM else None),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("criterion-case", "Answer", candidate_answer="Candidate")
    decision = guard.evaluate_output(context)
    assert decision.allowed is not required
    assert decision.results[-1].outcome == Outcome.VIOLATION
    if required:
        with pytest.raises(PolicyViolationError):
            guard.enforce_output(context)
    else:
        assert guard.enforce_output(context) == "Candidate"
