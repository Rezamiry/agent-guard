from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, PolicySet
from agent_guard.core.models import EvaluationContext
from agent_guard.evaluation.dataset import DatasetLineError, SavedExample
from agent_guard.evaluation.report import compare_results
from agent_guard.evaluation.runner import run_saved


class Detector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


def test_saved_answers_match_direct_guard_decisions_without_regeneration() -> None:
    guard = Guard(detector=Detector()).prepare()
    safe = SavedExample("safe", EvaluationContext("safe", "hello", candidate_answer="okay"))
    blocked = SavedExample("blocked", EvaluationContext("blocked", "hello",
                                                        candidate_answer="secret@example.com"))
    rows = (safe, DatasetLineError(2, "invalid_record"), blocked)
    expected = (guard.evaluate_output(safe.context), guard.evaluate_output(blocked.context))
    results = run_saved(guard, rows)
    assert len(results) == 3
    assert results[0].output_decision == expected[0]
    assert results[1].error_category == "invalid_record"
    assert results[2].output_decision == expected[1]
    assert safe.context.candidate_answer == "okay"
    assert blocked.context.candidate_answer == "secret@example.com"
    assert "secret@example.com" not in str(results)


def test_two_fixed_settings_change_saved_decision_without_mutating_live_policy() -> None:
    required_policy = PolicySet(id="comparison-v1")
    optional_policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT, required=False),
    ), id="comparison-v1")
    required_guard = Guard(required_policy, detector=Detector()).prepare()
    optional_guard = Guard(optional_policy, detector=Detector()).prepare()
    example = SavedExample("e3", EvaluationContext("e3", "hello",
                                                  candidate_answer="secret@example.com"))
    live_before = required_guard.evaluate_output(example.context)
    left = run_saved(required_guard, (example,))
    right = run_saved(optional_guard, (example,))
    comparison = compare_results(left, right)
    assert left[0].output_decision == live_before
    assert not left[0].output_decision.allowed
    assert right[0].output_decision.allowed
    assert comparison["changed_example_ids"] == ["e3"]
    assert comparison["left_settings_id"] != comparison["right_settings_id"]
    assert required_guard.policy is required_policy
    assert required_guard.evaluate_output(example.context) == live_before
    assert example.context.candidate_answer == "secret@example.com"
