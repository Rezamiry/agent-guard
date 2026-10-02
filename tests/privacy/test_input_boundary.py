"""Input boundary order and prohibited external calls."""

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.core.errors import EvaluationError, PolicyViolationError
from agent_guard.core.models import EvaluationContext, EvidenceItem


class SafeDetector:
    def detect(self, text: str) -> bool:
        return False


class EmailDetector:
    def __init__(self) -> None:
        self.seen: list[str] = []
        self.fail = False

    def detect(self, text: str) -> bool:
        self.seen.append(text)
        if self.fail:
            raise RuntimeError("sensitive provider text")
        return "secret@example.com" in text


class OrderedEvaluator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        self.calls.append(check.id)
        outcome = Outcome.VIOLATION if check.id == "injection" else Outcome.PASS
        return CheckResult(check.id, check.boundary, outcome, confidence=0.95)

    async def aevaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        return self.evaluate(check, context)


def make_guard(*, injection_required: bool) -> tuple[Guard, OrderedEvaluator]:
    evaluator = OrderedEvaluator()
    policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("injection", CheckKind.PROMPT_INJECTION, Boundary.INPUT,
                    required=injection_required),
        CheckPolicy("later", CheckKind.CUSTOM, Boundary.INPUT, criteria="Follow the approved tone."),
    ))
    return Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare(), evaluator


def test_required_semantic_failure_stops_later_remote_check() -> None:
    guard, evaluator = make_guard(injection_required=True)
    decision = guard.evaluate_input(EvaluationContext("r1", "safe question"))
    assert not decision.allowed
    assert evaluator.calls == ["injection"]
    assert [(result.check_id, result.outcome) for result in decision.results] == [
        ("pii_input", Outcome.PASS),
        ("injection", Outcome.VIOLATION),
        ("later", Outcome.SKIPPED),
    ]
    with pytest.raises(PolicyViolationError):
        guard.enforce_input(EvaluationContext("r1", "safe question"))


async def test_async_required_failure_stops_later_remote_check() -> None:
    guard, evaluator = make_guard(injection_required=True)
    decision = await guard.aevaluate_input(EvaluationContext("r2", "safe question"))
    assert not decision.allowed
    assert evaluator.calls == ["injection"]
    assert decision.results[-1].outcome == Outcome.SKIPPED


def test_optional_semantic_violation_does_not_stop_later_check() -> None:
    guard, evaluator = make_guard(injection_required=False)
    decision = guard.evaluate_input(EvaluationContext("r3", "safe question"))
    assert decision.allowed
    assert evaluator.calls == ["injection", "later"]
    assert decision.results[-1].outcome == Outcome.PASS


def test_default_local_only_checks_changed_assembled_input_before_handoff() -> None:
    detector = EmailDetector()
    guard = Guard(detector=detector).prepare()
    model_calls = 0

    def handoff(context: EvaluationContext) -> None:
        nonlocal model_calls
        guard.enforce_input(context)
        model_calls += 1

    handoff(EvaluationContext("r4", "summarize"))
    assert model_calls == 1
    assembled = EvaluationContext("r4", "summarize", messages=(
        {"role": "tool", "content": "source: secret@example.com"},
    ), evidence=(EvidenceItem("source", "secret@example.com", "future-generation"),))
    decision = guard.evaluate_input(assembled)
    assert not decision.allowed
    assert decision.results[0].outcome == Outcome.VIOLATION
    assert model_calls == 1
    assert "secret@example.com" in detector.seen[-1]


def test_required_detector_error_prevents_later_remote_judgment() -> None:
    detector = EmailDetector()
    evaluator = OrderedEvaluator()
    policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("injection", CheckKind.PROMPT_INJECTION, Boundary.INPUT),
    ))
    guard = Guard(policy, detector=detector, evaluator=evaluator).prepare()
    detector.fail = True
    decision = guard.evaluate_input(EvaluationContext("r5", "safe question"))
    assert not decision.allowed
    assert decision.results[0].outcome == Outcome.EVALUATION_ERROR
    assert decision.results[1].outcome == Outcome.SKIPPED
    assert evaluator.calls == []
    with pytest.raises(EvaluationError):
        guard.enforce_input(EvaluationContext("r5", "safe question"))
    assert evaluator.calls == []


def test_initial_required_pii_blocks_and_explicit_optional_pii_only_monitors() -> None:
    detector = EmailDetector()
    initial = EvaluationContext("r6", "secret@example.com")
    required = Guard(detector=detector).prepare()
    assert required.evaluate_input(initial).results[0].outcome == Outcome.VIOLATION
    model_calls = 0
    if required.evaluate_input(initial).allowed:
        model_calls += 1
    assert model_calls == 0

    optional_policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT, required=False),
    ))
    optional = Guard(optional_policy, detector=detector).prepare()
    decision = optional.evaluate_input(initial)
    assert decision.allowed
    assert decision.results[0].outcome == Outcome.VIOLATION
    detector.fail = True
    error_decision = optional.evaluate_input(initial)
    assert error_decision.allowed
    assert error_decision.results[0].outcome == Outcome.EVALUATION_ERROR


def test_explicit_request_field_is_inspected_even_when_message_hint_is_true() -> None:
    evaluator = OrderedEvaluator()
    policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("injection", CheckKind.PROMPT_INJECTION, Boundary.INPUT),
    ))
    guard = Guard(policy, detector=EmailDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("r7", "secret@example.com",
                                messages=({"role": "user", "content": "safe"},),
                                current_request_in_messages=True)
    decision = guard.evaluate_input(context)
    assert not decision.allowed
    assert evaluator.calls == []
