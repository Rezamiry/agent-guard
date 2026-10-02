from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.core.models import EvaluationContext, EvidenceItem


class SafeDetector:
    def detect(self, text: str) -> bool:
        return False


class RecordingEvaluator:
    def __init__(self) -> None:
        self.evidence_ids: list[tuple[str, ...]] = []

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        self.evidence_ids.append(tuple(item.id for item in context.evidence))
        return CheckResult(check.id, check.boundary, Outcome.PASS,
                           confidence=0.9, evaluator="controlled-v1")


def test_groundedness_uses_only_identified_current_generation_evidence() -> None:
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("grounded", CheckKind.GROUNDEDNESS, Boundary.OUTPUT),
    ))
    evaluator = RecordingEvaluator()
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    old = EvidenceItem("old", "Unrelated text", "generation-old")
    matching = EvidenceItem("current", "Relevant text", "generation-current")
    context = EvaluationContext("r1", "What is in the report?", candidate_answer="It is ready.",
                                evidence=(old,), generation_id="generation-current")
    decision = guard.evaluate_output(context)
    assert decision.results[-1].outcome == Outcome.SKIPPED
    assert evaluator.evidence_ids == []
    with_evidence = EvaluationContext("r2", "What is in the report?",
                                      candidate_answer="It is ready.", evidence=(old, matching),
                                      generation_id="generation-current")
    assert guard.evaluate_output(with_evidence).allowed
    assert evaluator.evidence_ids == [("current",)]


def test_default_semantic_confidence_threshold_and_metadata() -> None:
    class ScoredEvaluator:
        def __init__(self) -> None:
            self.score = 0.80

        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
            return CheckResult(check.id, check.boundary, Outcome.PASS,
                               confidence=self.score, evaluator="controlled-v1",
                               cost=0.01, input_tokens=10, output_tokens=2)

    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    evaluator = ScoredEvaluator()
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("r3", "What?", candidate_answer="A safe reply.")
    passing = guard.evaluate_output(context).results[-1]
    assert passing.outcome == Outcome.PASS
    assert (passing.evaluator, passing.cost, passing.input_tokens) == ("controlled-v1", 0.01, 10)
    evaluator.score = 0.79
    assert guard.evaluate_output(context).results[-1].outcome == Outcome.INCONCLUSIVE


def test_relevance_evaluator_receives_current_request_and_assembled_context() -> None:
    class ContextEvaluator:
        def __init__(self) -> None:
            self.seen: list[EvaluationContext] = []

        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
            self.seen.append(context)
            return CheckResult(check.id, check.boundary, Outcome.VIOLATION, confidence=0.95)

    evaluator = ContextEvaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    context = EvaluationContext("r4", "Which report?", messages=(
        {"role": "user", "content": "Please summarize the quarterly report"},
    ), candidate_answer="The weather is sunny.")
    decision = guard.evaluate_output(context)
    assert not decision.allowed
    assert evaluator.seen[0].current_request == "Which report?"
    assert evaluator.seen[0].messages == context.messages
    assert evaluator.seen[0].candidate_answer == "The weather is sunny."


def test_required_and_optional_safety_custom_outcomes() -> None:
    class ScriptedEvaluator:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
            self.calls.append(check.id)
            outcome = Outcome.VIOLATION if check.kind == CheckKind.CONTENT_SAFETY else Outcome.PASS
            return CheckResult(check.id, check.boundary, outcome, confidence=0.95)

    context = EvaluationContext("r5", "safe request", candidate_answer="answer")
    evaluator = ScriptedEvaluator()
    required_policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("safety", CheckKind.CONTENT_SAFETY, Boundary.OUTPUT),
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT, criteria="Use a neutral tone."),
    ))
    decision = Guard(required_policy, detector=SafeDetector(), evaluator=evaluator).prepare().evaluate_output(
        context
    )
    assert not decision.allowed
    assert evaluator.calls == ["safety"]
    assert decision.results[-1].outcome == Outcome.SKIPPED

    optional_evaluator = ScriptedEvaluator()
    optional_policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("safety", CheckKind.CONTENT_SAFETY, Boundary.OUTPUT, required=False),
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT, criteria="Use a neutral tone."),
    ))
    decision = Guard(optional_policy, detector=SafeDetector(), evaluator=optional_evaluator
                     ).prepare().evaluate_output(context)
    assert decision.allowed
    assert optional_evaluator.calls == ["safety", "custom"]
    assert decision.results[-1].outcome == Outcome.PASS


def test_missing_required_evidence_skips_later_external_judgment() -> None:
    class CountingEvaluator:
        def __init__(self) -> None:
            self.calls = 0

        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
            self.calls += 1
            return CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.95)

    evaluator = CountingEvaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("grounded", CheckKind.GROUNDEDNESS, Boundary.OUTPUT),
        CheckPolicy("later", CheckKind.CUSTOM, Boundary.OUTPUT, criteria="Neutral tone."),
    ), evidence_required=True)
    guard = Guard(policy, detector=SafeDetector(), evaluator=evaluator).prepare()
    decision = guard.evaluate_output(EvaluationContext("r6", "What happened?",
                                                       candidate_answer="A brief answer."))
    assert not decision.allowed
    assert decision.results[-2].outcome == Outcome.SKIPPED
    assert decision.results[-1].outcome == Outcome.SKIPPED
    assert evaluator.calls == 0


async def test_async_missing_required_evidence_skips_later_external_judgment() -> None:
    class CountingEvaluator:
        def __init__(self) -> None:
            self.calls = 0

        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
            self.calls += 1
            return CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.95)

    evaluator = CountingEvaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("grounded", CheckKind.GROUNDEDNESS, Boundary.OUTPUT),
        CheckPolicy("later", CheckKind.CUSTOM, Boundary.OUTPUT, criteria="Neutral tone."),
    ), evidence_required=True)
    guard = await Guard(policy, detector=SafeDetector(), evaluator=evaluator).aprepare()
    decision = await guard.aevaluate_output(EvaluationContext("r7", "What happened?",
                                                             candidate_answer="A brief answer."))
    assert not decision.allowed
    assert decision.results[-2].outcome == Outcome.SKIPPED
    assert decision.results[-1].outcome == Outcome.SKIPPED
    assert evaluator.calls == 0
