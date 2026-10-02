"""Privacy of the candidate and every output-evaluator field."""

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.core.errors import PolicyViolationError
from agent_guard.core.models import EvaluationContext, EvidenceItem


class EmailDetector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


class Evaluator:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        self.calls += 1
        return CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.95)


def test_explicit_request_field_is_checked_before_output_evaluation() -> None:
    evaluator = Evaluator()
    policy = PolicySet(checks=(
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT),
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=EmailDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("r8", "secret@example.com", candidate_answer="safe answer",
                                messages=({"role": "user", "content": "safe"},),
                                current_request_in_messages=True)
    decision = guard.evaluate_output(context)
    assert not decision.allowed
    assert evaluator.calls == 0


@pytest.mark.parametrize("contaminated", ["answer", "evidence", "tool_description"])
def test_output_pii_withholds_delivery_without_reversing_prior_effects(contaminated: str) -> None:
    evaluator = Evaluator()
    policy = PolicySet(checks=(
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT),
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=EmailDetector(), evaluator=evaluator).prepare()
    prior_tool_effects = 1
    context = EvaluationContext(
        "r9", "summarize", candidate_answer=(
            "secret@example.com" if contaminated == "answer" else "safe answer"
        ),
        evidence=(EvidenceItem("source", "secret@example.com", "generation"),)
        if contaminated == "evidence" else (),
        generation_id="generation",
        tool_descriptions=("secret@example.com",) if contaminated == "tool_description" else (),
    )
    with pytest.raises(PolicyViolationError):
        guard.enforce_output(context)
    assert evaluator.calls == 0
    assert prior_tool_effects == 1
