import httpx

from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, Outcome, PolicySet
from agent_guard.core.models import EvaluationContext
from agent_guard.providers.jev import JevEvaluator


class EmailDetector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


async def test_guard_preflights_before_one_jev_attempt() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={
            "model": "typesafe/jev-1.13",
            "answers": {"relevance": {"type": "choice", "choice": "pass", "confidence": 0.9}},
            "usage": {"input_tokens": 10, "output_tokens": 2},
        })

    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    evaluator = JevEvaluator("token", transport=httpx.MockTransport(handler))
    guard = await Guard(policy, detector=EmailDetector(), evaluator=evaluator).aprepare()
    try:
        safe = EvaluationContext("r1", "What?", candidate_answer="A safe answer")
        decision = await guard.aevaluate_output(safe)
        assert decision.allowed
        assert decision.results[-1].outcome == Outcome.PASS
        assert calls == 1
        blocked = EvaluationContext("r2", "What?", candidate_answer="secret@example.com")
        decision = await guard.aevaluate_output(blocked)
        assert not decision.allowed
        assert calls == 1
    finally:
        await guard.aclose()
