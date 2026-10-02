"""Controlled final-answer examples with identified evidence and a permitted refusal."""

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.core.models import EvaluationContext, EvidenceItem


class ControlledEvaluator:
    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        outcome = Outcome.PASS
        if check.kind == CheckKind.RELEVANCE and context.candidate_answer == "Unrelated answer":
            outcome = Outcome.VIOLATION
        return CheckResult(check.id, check.boundary, outcome, check.required,
                           outcome.value, confidence=0.9, evaluator="controlled-v1")


def main() -> None:
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
        CheckPolicy("groundedness", CheckKind.GROUNDEDNESS, Boundary.OUTPUT),
    ))
    guard = Guard(policy, detector=LocalPIIDetector(), evaluator=ControlledEvaluator()).prepare()
    try:
        evidence = (EvidenceItem("report", "The report is ready.", "generation-1"),)
        backed = EvaluationContext("example-1", "What is the report status?",
                                   candidate_answer="The report is ready.", evidence=evidence,
                                   generation_id="generation-1")
        print("evidence-backed:", guard.enforce_output(backed))
        missing = EvaluationContext("example-2", "What is the report status?",
                                    candidate_answer="I cannot confirm without the report.",
                                    generation_id="generation-2")
        decision = guard.evaluate_output(missing)
        print("missing evidence:", decision.results[-1].outcome.value)
        print("permitted clarification:", guard.enforce_output(missing))
    finally:
        guard.close()


if __name__ == "__main__":
    main()
