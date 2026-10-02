import json
from hashlib import sha256

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, PolicySet
from agent_guard.core.models import BoundaryDecision, EvaluationContext, EvidenceItem
from agent_guard.evaluation.dataset import SavedExample
from agent_guard.evaluation.metrics import MetricRow, summarize
from agent_guard.evaluation.report import compare_results, csv_summary, json_report
from agent_guard.evaluation.runner import OfflineResult, run_saved


class Detector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


def test_reports_exclude_content_and_preserve_unknown_cost() -> None:
    guard = Guard(detector=Detector()).prepare()
    example = SavedExample("e1", EvaluationContext("e1", "hello",
                                                   candidate_answer="secret@example.com"))
    results = run_saved(guard, (example,))
    report = json_report(results)
    parsed = json.loads(report)
    assert parsed["examples"][0]["example_id"] == "e1"
    assert parsed["examples"][0]["decision"] == "block"
    assert parsed["examples"][0]["settings_id"] == guard.policy.settings_id
    assert parsed["examples"][0]["checks"][0]["settings_id"] == guard.policy.settings_id
    assert parsed["examples"][0]["checks"][0]["cost"] is None
    assert "secret@example.com" not in report
    assert "credential" not in report


def test_csv_aggregate_and_comparison_use_safe_ids() -> None:
    guard = Guard(detector=Detector()).prepare()
    example = SavedExample("e1", EvaluationContext("e1", "hello", candidate_answer="safe"))
    left = run_saved(guard, (example,))
    blocked = SavedExample("e1", EvaluationContext("e1", "hello",
                                                   candidate_answer="secret@example.com"))
    right = run_saved(guard, (blocked,))
    comparison = compare_results(left, right)
    assert comparison["changed_example_ids"] == ["e1"]
    assert comparison["left_counts"] == {"allow": 1, "block": 0, "error": 0}
    assert comparison["right_counts"] == {"allow": 0, "block": 1, "error": 0}
    assert "secret@example.com" not in str(comparison)
    from agent_guard import Boundary, Outcome
    metrics = summarize((MetricRow("e1", "default-v1", Boundary.OUTPUT,
                                   Outcome.PASS, Outcome.PASS),),
                        policy_id="default-v1", boundary=Boundary.OUTPUT)
    csv = csv_summary(metrics)
    assert "default-v1" in csv
    assert "accuracy" in csv


def test_report_rejects_untrusted_reason_or_metric_value() -> None:
    with pytest.raises(ValueError):
        json_report((OfflineResult("e1", "p1", BoundaryDecision(False, (),
                                                                "secret@example.com")),))
    with pytest.raises(ValueError):
        csv_summary({"policy_id": "p1", "boundary": "output",
                     "accuracy": "secret@example.com"})


def test_comparison_rejects_unsafe_duplicate_or_reordered_ids() -> None:
    allowed = BoundaryDecision(True, (), "allow")
    unsafe = OfflineResult("secret@example.com", "p1", allowed)
    with pytest.raises(ValueError):
        compare_results((unsafe,), (unsafe,))

    first = OfflineResult("e1", "p1", allowed)
    second = OfflineResult("e2", "p1", allowed)
    with pytest.raises(ValueError):
        compare_results((first, first), (first, first))
    with pytest.raises(ValueError):
        compare_results((first, second), (second, first))


def test_same_policy_id_with_different_declared_settings_is_distinguishable() -> None:
    example = SavedExample("e3", EvaluationContext("e3", "hello",
                                                  candidate_answer="secret@example.com"))
    required = Guard(detector=Detector()).prepare()
    optional_policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT, required=False),
    ))
    optional = Guard(optional_policy, detector=Detector()).prepare()
    left = run_saved(required, (example,))
    right = run_saved(optional, (example,))
    comparison = compare_results(left, right)
    assert comparison["changed_example_ids"] == ["e3"]
    assert comparison["left_policy_id"] == comparison["right_policy_id"] == "default-v1"
    assert comparison["left_settings_id"] == required.policy.settings_id
    assert comparison["right_settings_id"] == optional.policy.settings_id
    assert comparison["left_settings_id"] != comparison["right_settings_id"]
    assert "secret@example.com" not in str(comparison)


def test_report_excludes_request_evidence_hashes_and_arbitrary_evaluator_text() -> None:
    class SafeDetector:
        def detect(self, text: str) -> bool:
            return False

    class BrokenEvaluator:
        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> object:
            raise RuntimeError("rationale=do not expose; credential=top-secret")

    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT, required=False),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=BrokenEvaluator()).prepare()
    raw = ("request-sentinel@example.com", "answer-sentinel@example.com",
           "evidence-sentinel@example.com")
    example = SavedExample("privacy-case", EvaluationContext(
        "privacy-case", raw[0], candidate_answer=raw[1],
        evidence=(EvidenceItem("source", raw[2], "generation"),),
        generation_id="generation",
    ))
    report = json_report(run_saved(guard, (example,)))
    parsed = json.loads(report)
    assert parsed["examples"][0]["checks"][-1]["cost"] is None
    assert parsed["examples"][0]["checks"][-1]["error_category"] == "evaluator_error"
    for value in (*raw, "top-secret", "rationale=do not expose"):
        assert value not in report
    for value in raw:
        assert sha256(value.encode()).hexdigest() not in report
