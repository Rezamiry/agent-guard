"""Local input preflight with a prepared detector and no external evaluator."""

from agent_guard import Guard
from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.core.models import EvaluationContext


def main() -> None:
    guard = Guard(detector=LocalPIIDetector()).prepare()
    try:
        for request in ("Summarize the report", "Contact jane@example.com"):
            decision = guard.evaluate_input(EvaluationContext("example", request))
            print("allow" if decision.allowed else "block")
    finally:
        guard.close()


if __name__ == "__main__":
    main()
