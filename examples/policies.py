"""Required versus optional monitoring and a sanitized runtime failure."""

from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, PolicySet
from agent_guard.core.errors import EvaluationError
from agent_guard.core.models import EvaluationContext


class ControlledDetector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


class FailingEvaluator:
    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> object:
        raise EvaluationError("provider_timeout")


def main() -> None:
    optional = PolicySet(
        id="monitor-v1",
        checks=(
            CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT, required=False),
            CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT),
            CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT, required=False),
        ),
    )
    guard = Guard(optional, detector=ControlledDetector(), evaluator=FailingEvaluator()).prepare()
    try:
        monitored = guard.evaluate_input(EvaluationContext("example-1", "secret@example.com"))
        print("optional PII monitoring:", monitored.allowed, monitored.results[0].outcome.value)
        output = guard.evaluate_output(EvaluationContext("example-2", "hello",
                                                         candidate_answer="safe"))
        print("optional provider failure:", output.allowed, output.results[-1].reason_code)
    finally:
        guard.close()


if __name__ == "__main__":
    main()
