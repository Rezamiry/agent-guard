import json

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.core.errors import ConfigurationError, EvaluationError, IntegrationError
from agent_guard.core.models import EvaluationContext
from agent_guard.core.records import record_for


def test_record_contains_only_safe_identifiers_and_unknown_cost() -> None:
    result = CheckResult(
        "pii_input", Boundary.INPUT, Outcome.EVALUATION_ERROR, True, "detector_error",
        elapsed_seconds=0.25, error_category="detector_unavailable",
    )
    record = record_for(
        result, policy_id="policy-v1", content="secret@example.com", credential="top-secret"
    )
    assert record["check"] == "pii_input"
    assert record["policy"] == "policy-v1"
    assert record["cost"] is None
    assert "secret@example.com" not in str(record)
    assert "top-secret" not in str(record)


def test_record_rejects_content_bearing_policy_or_reason_ids() -> None:
    result = CheckResult("pii_input", Boundary.INPUT, Outcome.PASS, True, "pass")
    with pytest.raises(ValueError):
        record_for(result, policy_id="secret@example.com")
    with pytest.raises(ValueError):
        CheckResult("pii_input", Boundary.INPUT, Outcome.PASS, True, "secret@example.com")


def test_record_rejects_untrusted_metadata() -> None:
    with pytest.raises(ValueError):
        CheckResult("pii_input", Boundary.INPUT, Outcome.PASS, evaluator="secret@example.com")
    with pytest.raises(ValueError):
        CheckResult("pii_input", Boundary.INPUT, Outcome.EVALUATION_ERROR,
                    error_category="secret@example.com")
    with pytest.raises(ValueError):
        CheckResult("pii_input", Boundary.INPUT, Outcome.PASS, cost=-1)


def test_provider_failure_record_drops_raw_text_and_state_does_not_cross_requests() -> None:
    class Detector:
        def __init__(self) -> None:
            self.fail = True

        def detect(self, text: str) -> bool:
            if self.fail:
                raise RuntimeError("provider said secret@example.com; token=top-secret")
            return False

    detector = Detector()
    guard = Guard(detector=detector).prepare()
    first = guard.evaluate_input(EvaluationContext("request-one-unique", "secret@example.com"))
    first_record = record_for(first.results[0], policy_id="policy-v1",
                              content="secret@example.com", credential="top-secret")
    assert first_record["outcome"] == "evaluation_error"
    assert first_record["error_category"] == "detector_error"
    assert first_record["cost"] is None
    detector.fail = False
    second = guard.evaluate_input(EvaluationContext("request-two-unique", "safe"))
    second_record = record_for(second.results[0], policy_id="policy-v1")
    assert second_record["outcome"] == "pass"
    assert second_record["error_category"] is None
    for record in (first_record, second_record):
        serialized = json.dumps(record)
        assert "secret@example.com" not in serialized
        assert "top-secret" not in serialized
        assert "provider said" not in serialized
        assert "request-one-unique" not in serialized
        assert "request-two-unique" not in serialized


def test_optional_provider_error_is_recorded_but_integration_fault_is_not() -> None:
    class SafeDetector:
        def detect(self, text: str) -> bool:
            return False

    class FailingEvaluator:
        def __init__(self) -> None:
            self.integration_fault = False

        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> Outcome:
            if self.integration_fault:
                raise IntegrationError("native_extraction_failed")
            raise EvaluationError("provider_timeout")

    evaluator = FailingEvaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT, required=False),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("r3", "hello", candidate_answer="safe")
    decision = guard.evaluate_output(context)
    assert decision.allowed
    result = decision.results[-1]
    record = record_for(result, policy_id=policy.id, settings_id=policy.settings_id)
    assert record["outcome"] == "evaluation_error"
    assert record["error_category"] == "provider_timeout"
    assert record["cost"] is None
    assert record["settings_id"] == policy.settings_id
    evaluator.integration_fault = True
    with pytest.raises(IntegrationError):
        guard.evaluate_output(context)
    with pytest.raises(ConfigurationError):
        Guard(policy, detector=SafeDetector()).prepare()
