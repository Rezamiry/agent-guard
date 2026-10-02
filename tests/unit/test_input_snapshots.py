import pytest

from agent_guard import Guard
from agent_guard.core.errors import IntegrationError
from agent_guard.core.models import EvaluationContext, EvidenceItem


class SafeDetector:
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, text: str) -> bool:
        self.calls += 1
        return False


def test_all_identified_evidence_counts_toward_context_limit() -> None:
    guard = Guard(detector=SafeDetector()).prepare()
    allowed = tuple(EvidenceItem(f"e{i}", "x", "current") for i in range(64))
    context = EvaluationContext("r1", "hello", candidate_answer="safe",
                                evidence=allowed, generation_id="current")
    assert guard.evaluate_output(context).allowed
    overflow = allowed + (EvidenceItem("old", "x", "earlier"),)
    context = EvaluationContext("r2", "hello", candidate_answer="safe",
                                evidence=overflow, generation_id="current")
    with pytest.raises(IntegrationError):
        guard.evaluate_output(context)


def test_input_exact_code_point_limit_passes_and_overflow_rejects_before_detector() -> None:
    detector = SafeDetector()
    guard = Guard(detector=detector).prepare()
    exact = "e\u0301" * 50_000
    assert len(exact) == 100_000
    assert guard.evaluate_input(EvaluationContext("exact", exact)).allowed
    assert detector.calls == 1
    with pytest.raises(IntegrationError):
        guard.evaluate_input(EvaluationContext("overflow", exact + "x"))
    assert detector.calls == 1


def test_input_message_and_evidence_limits_reject_before_detector() -> None:
    detector = SafeDetector()
    guard = Guard(detector=detector).prepare()
    messages = tuple({"role": "user", "content": ""} for _ in range(128))
    evidence = tuple(EvidenceItem(f"e{i}", "", "generation") for i in range(64))
    assert guard.evaluate_input(EvaluationContext("exact", "", messages=messages,
                                                  evidence=evidence)).allowed
    assert detector.calls == 1
    with pytest.raises(IntegrationError):
        guard.evaluate_input(EvaluationContext("message-overflow", "", messages=messages + (
            {"role": "user", "content": ""},
        )))
    with pytest.raises(IntegrationError):
        guard.evaluate_input(EvaluationContext("evidence-overflow", "", evidence=evidence + (
            EvidenceItem("extra", "", "generation"),
        )))
    assert detector.calls == 1
