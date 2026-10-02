import re

from agent_guard import Guard
from agent_guard.core.models import EvaluationContext


class BoundaryDetector:
    def detect(self, text: str) -> bool:
        return bool(re.search(r"(?<![\w.+-])secret@example\.com", text))


def test_separate_tool_part_starts_with_email_and_is_still_detected() -> None:
    guard = Guard(detector=BoundaryDetector()).prepare()
    context = EvaluationContext("r1", "hello", messages=(
        {"role": "tool", "content": "secret@example.com"},
    ))
    assert not guard.evaluate_input(context).allowed
