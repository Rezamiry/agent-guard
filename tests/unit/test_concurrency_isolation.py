"""Overlapping requests must not mix content, evidence, policy, or records (FR-25, AC-21)."""

import asyncio

from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, Outcome, PolicySet
from agent_guard.core.models import CheckResult, EvaluationContext, EvidenceItem


class RecordingEvaluator:
    """Reports what each concurrent call actually saw, keyed by its own request."""

    def __init__(self) -> None:
        self.seen: dict[str, tuple[str, ...]] = {}

    async def aevaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        await asyncio.sleep(0.01)
        self.seen[context.request_id] = tuple(item.id for item in context.evidence)
        outcome = Outcome.VIOLATION if "blocked" in context.request_id else Outcome.PASS
        return CheckResult(check.id, check.boundary, outcome, confidence=0.99)


class SafeDetector:
    def detect(self, text: str) -> bool:
        return False


def _output_policy() -> PolicySet:
    return PolicySet(checks=PolicySet().checks + (
        CheckPolicy("grounded", CheckKind.GROUNDEDNESS, Boundary.OUTPUT),
    ))


async def test_concurrent_output_evaluations_isolate_evidence_and_decisions() -> None:
    evaluator = RecordingEvaluator()
    guard = await Guard(_output_policy(), detector=SafeDetector(),
                        evaluator=evaluator).aprepare()
    contexts = [
        EvaluationContext(f"safe-{i}", f"question {i}", candidate_answer=f"answer {i}",
                          evidence=(EvidenceItem(f"evidence-{i}", f"text {i}", "gen"),),
                          generation_id="gen")
        for i in range(4)
    ] + [
        EvaluationContext(f"blocked-{i}", f"question {i}", candidate_answer=f"answer {i}",
                          evidence=(EvidenceItem(f"blocked-evidence-{i}", f"text {i}", "gen"),),
                          generation_id="gen")
        for i in range(4)
    ]
    decisions = await asyncio.gather(*(guard.aevaluate_output(c) for c in contexts))
    for context, decision in zip(contexts, decisions, strict=True):
        assert decision.allowed == context.request_id.startswith("safe")
        # Each request's recorded evidence must contain only its own evidence id.
        assert evaluator.seen[context.request_id] == tuple(item.id for item in context.evidence)
    all_seen_ids = {eid for ids in evaluator.seen.values() for eid in ids}
    assert len(all_seen_ids) == len(contexts)
    await guard.aclose()


async def test_concurrent_guards_with_different_policies_do_not_share_check_sets() -> None:
    strict_policy = PolicySet(id="strict", checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT),
    ))
    lenient_policy = PolicySet(id="lenient", checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT, required=False),
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT, required=False),
    ))

    class PIIDetector:
        def detect(self, text: str) -> bool:
            return "secret@example.com" in text

    strict_guard = await Guard(strict_policy, detector=PIIDetector()).aprepare()
    lenient_guard = await Guard(lenient_policy, detector=PIIDetector()).aprepare()

    async def run(guard: Guard, request_id: str) -> bool:
        return (await guard.aevaluate_input(
            EvaluationContext(request_id, "secret@example.com"))).allowed

    results = await asyncio.gather(
        run(strict_guard, "s1"), run(lenient_guard, "l1"),
        run(strict_guard, "s2"), run(lenient_guard, "l2"),
    )
    assert results == [False, True, False, True]
    assert strict_guard.policy is strict_policy
    assert lenient_guard.policy is lenient_policy
    await strict_guard.aclose()
    await lenient_guard.aclose()
