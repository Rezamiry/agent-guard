import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, Outcome, PolicySet
from agent_guard.core.errors import PolicyViolationError
from agent_guard.core.models import EvaluationContext, EvidenceItem


class Detector:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def detect(self, text: str) -> bool:
        self.seen.append(text)
        return "secret@example.com" in text


class Evaluator:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> Outcome:
        self.calls += 1
        return Outcome.PASS


def test_required_input_pii_blocks_before_remote_check() -> None:
    detector, evaluator = Detector(), Evaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("injection", CheckKind.PROMPT_INJECTION, Boundary.INPUT),
    ))
    guard = Guard(policy, detector=detector, evaluator=evaluator).prepare()
    context = EvaluationContext("r1", "summarize", messages=(
        {"role": "tool", "content": "secret@example.com"},
    ))
    decision = guard.evaluate_input(context)
    assert not decision.allowed
    assert decision.results[0].outcome == Outcome.VIOLATION
    assert evaluator.calls == 0
    with pytest.raises(PolicyViolationError):
        guard.enforce_input(context)


def test_optional_input_pii_is_recorded_and_safe_input_rechecked() -> None:
    detector = Detector()
    policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT, required=False),
    ))
    guard = Guard(policy, detector=detector).prepare()
    bad = EvaluationContext("r1", "secret@example.com")
    safe = EvaluationContext("r1", "hello")
    assert guard.evaluate_input(bad).allowed
    assert guard.evaluate_input(bad).results[0].outcome == Outcome.VIOLATION
    assert guard.evaluate_input(safe).allowed
    assert detector.seen[-1] == "hello"


def test_output_pii_blocks_delivery_and_safe_answer_is_unchanged() -> None:
    detector = Detector()
    guard = Guard(detector=detector).prepare()
    bad = EvaluationContext("r1", "hello", candidate_answer="secret@example.com")
    assert not guard.evaluate_output(bad).allowed
    with pytest.raises(PolicyViolationError):
        guard.enforce_output(bad)
    safe = EvaluationContext("r2", "hello", candidate_answer="Safe answer")
    assert guard.enforce_output(safe) == "Safe answer"


def test_custom_criteria_are_locally_inspected_before_remote_judgment() -> None:
    detector, evaluator = Detector(), Evaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT,
                    criteria="Avoid secret@example.com"),
    ))
    guard = Guard(policy, detector=detector, evaluator=evaluator).prepare()
    context = EvaluationContext("r3", "hello", candidate_answer="safe")
    assert not guard.evaluate_output(context).allowed
    assert evaluator.calls == 0


def test_tool_argument_key_is_inspected_before_input_handoff() -> None:
    guard = Guard(detector=Detector()).prepare()
    context = EvaluationContext("tool-1", "hello", tool_arguments=({"secret@example.com": 1},))
    assert not guard.evaluate_input(context).allowed


async def test_pre_generation_retrieved_evidence_is_inspected_before_remote_check() -> None:
    detector, evaluator = Detector(), Evaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("injection", CheckKind.PROMPT_INJECTION, Boundary.INPUT),
    ))
    guard = Guard(policy, detector=detector, evaluator=evaluator).prepare()
    context = EvaluationContext(
        "retrieved-1", "summarize", evidence=(
            EvidenceItem("source-1", "secret@example.com", "future-generation"),
        ),
    )
    assert not guard.evaluate_input(context).allowed
    assert not (await guard.aevaluate_input(context)).allowed
    assert evaluator.calls == 0
