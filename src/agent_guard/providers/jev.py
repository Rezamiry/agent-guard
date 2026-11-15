"""OpenRouter Decisions choice request and response validation."""

import re
from collections.abc import Mapping
from math import isfinite

import httpx

from agent_guard.checks.semantic import RUBRIC_VERSION, rubric_for
from agent_guard.core.errors import EvaluationError
from agent_guard.core.models import CheckPolicy, CheckResult, EvaluationContext, Outcome
from agent_guard.providers.transport import JevTransport

MODEL = "typesafe/jev-1.13"
# The service may report the pinned model as a dated snapshot, e.g. "typesafe/jev-1.13-20260917".
_MODEL_RESPONSE = re.compile(r"typesafe/jev-1\.13(-\d{8})?")


class JevEvaluator:
    def __init__(self, credential: str, *, timeout: float = 10.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = JevTransport(credential, timeout=timeout, transport=transport)

    def prepare(self) -> None:
        self.transport.prepare()

    async def aprepare(self) -> None:
        await self.transport.aprepare()

    async def aevaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        payload = build_choice_request(check, context)
        data = await self.transport.apost(payload)
        return parse_choice_response(data, check)

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        payload = build_choice_request(check, context)
        data = self.transport.post(payload)
        return parse_choice_response(data, check)

    async def aclose(self) -> None:
        await self.transport.aclose()

    def close(self) -> None:
        self.transport.close()


def build_choice_request(check: CheckPolicy, context: EvaluationContext) -> dict[str, object]:
    passed, violated = rubric_for(check)
    instructions = f"Agent Guard semantic rubric {RUBRIC_VERSION}. Use only the supplied state and criteria."
    if check.criteria is not None:
        instructions += " Governing custom criterion: " + check.criteria
    state: dict[str, object] = {
        "current_request": context.current_request,
        "messages": list(context.messages),
        "evidence": [{"id": item.id, "text": item.text} for item in context.evidence],
        "tool_descriptions": list(context.tool_descriptions),
        "tool_arguments": list(context.tool_arguments),
    }
    if context.candidate_answer is not None:
        state["candidate_answer"] = context.candidate_answer
    return {
        "model": MODEL,
        "questions": {check.id: {"type": "choice", "instructions": instructions,
                                 "criteria": {"pass": passed, "violation": violated}}},
        "state": state,
        "provider": {"allow_fallbacks": False},
    }


def parse_choice_response(data: object, check: CheckPolicy) -> CheckResult:
    if not isinstance(data, Mapping) or not isinstance(data.get("model"), str) or (
        _MODEL_RESPONSE.fullmatch(data["model"]) is None
    ):
        raise EvaluationError("provider_response_invalid")
    answers = data.get("answers")
    if not isinstance(answers, Mapping) or set(answers) != {check.id}:
        raise EvaluationError("provider_response_invalid")
    answer = answers[check.id]
    if not isinstance(answer, Mapping) or answer.get("type") != "choice":
        raise EvaluationError("provider_response_invalid")
    choice = answer.get("choice")
    confidence = answer.get("confidence")
    if choice not in ("pass", "violation") or not isinstance(confidence, (int, float)) or (
        isinstance(confidence, bool) or not isfinite(confidence) or not 0 <= confidence <= 1
    ):
        raise EvaluationError("provider_response_invalid")
    usage = data.get("usage")
    if not isinstance(usage, Mapping):
        raise EvaluationError("provider_response_invalid")
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    cost = usage.get("cost")
    if (type(input_tokens) is not int or input_tokens < 0
        or type(output_tokens) is not int or output_tokens < 0
        or (cost is not None and (
            type(cost) not in (int, float) or not isfinite(cost) or cost < 0
        ))):
        raise EvaluationError("provider_response_invalid")
    minimum = check.minimum_confidence if check.minimum_confidence is not None else 0.8
    outcome = Outcome.INCONCLUSIVE if confidence < minimum else Outcome(choice)
    return CheckResult(
        check.id, check.boundary, outcome, check.required, outcome.value,
        confidence=float(confidence), evaluator=MODEL, cost=float(cost) if cost is not None else None,
        input_tokens=input_tokens, output_tokens=output_tokens,
    )
