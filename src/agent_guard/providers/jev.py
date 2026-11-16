"""OpenRouter Decisions choice request and response validation."""

import os
import re
from collections.abc import Mapping
from math import isfinite

import httpx

from agent_guard.checks.semantic import RUBRIC_VERSION, rubric_for
from agent_guard.core.errors import ConfigurationError, EvaluationError
from agent_guard.core.models import CheckPolicy, CheckResult, EvaluationContext, Outcome
from agent_guard.providers.transport import JevTransport

DEFAULT_MODEL = "typesafe/jev-1.13"
MODEL = DEFAULT_MODEL
PRIMARY_ENV_MODEL = "AGENT_GUARD_DECISION_MODEL"
FALLBACK_ENV_MODEL = "DECISION_MODEL"

# The service may report the pinned model as a dated snapshot, e.g. "typesafe/jev-1.13-20260917".
_MODEL_RESPONSE = re.compile(r"typesafe/jev-1\.13(-\d{8})?")
_MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$")

SUPPORTED_DECISION_MODELS: dict[str, dict[str, str]] = {
    "typesafe/jev-1.13": {
        "provider": "TypeSafe",
        "modality": "text",
        "description": "Pinned default decision model; calibrated for policy checks.",
    },
    "typesafe/jev-1.14": {
        "provider": "TypeSafe",
        "modality": "text",
        "description": "Updated reasoning and calibrated confidence for borderline policies.",
    },
    "google/gemini-decision-1": {
        "provider": "Google",
        "modality": "multimodal",
        "description": "High-throughput, low latency, expansive context window.",
    },
    "perplexity/decider-v1.2": {
        "provider": "Perplexity",
        "modality": "text",
        "description": "Groundedness and factual relevance evaluation.",
    },
    "perplexity/decider-flash-v1.3": {
        "provider": "Perplexity",
        "modality": "text",
        "description": "Ultra-low latency decision model for real-time guardrails.",
    },
    "cloudflare/clef-flash": {
        "provider": "Cloudflare",
        "modality": "text",
        "description": "Fast edge decision model; cost-effective preflight gating.",
    },
    "parallel/decisions-fast": {
        "provider": "Parallel",
        "modality": "text",
        "description": "Fast classification, prompt injection, and routing.",
    },
    "nace-ai/drex-max": {
        "provider": "Nace AI",
        "modality": "text",
        "description": "Complex policy rules and multi-step reasoning.",
    },
    "nace-ai/drex-v2.0": {
        "provider": "Nace AI",
        "modality": "text",
        "description": "Enhanced multi-step decision model.",
    },
    "liquid/d1": {
        "provider": "Liquid AI",
        "modality": "text",
        "description": "Efficient linear-state evaluation.",
    },
    "openai/gpt-6-luna-decisions": {
        "provider": "OpenAI",
        "modality": "text",
        "description": "Calibrated decision model via OpenRouter Decisions.",
    },
    "heygen/decision-1": {
        "provider": "HeyGen",
        "modality": "text",
        "description": "Structured policy and routing decision model.",
    },
}


def resolve_decision_model(model: str | None = None) -> str:
    if model is not None:
        candidate = model.strip()
        if not candidate or _MODEL_PATTERN.fullmatch(candidate) is None:
            raise ConfigurationError("invalid_decision_model")
        return candidate
    env_candidate = os.getenv(PRIMARY_ENV_MODEL) or os.getenv(FALLBACK_ENV_MODEL)
    if env_candidate is not None:
        candidate = env_candidate.strip()
        if not candidate or _MODEL_PATTERN.fullmatch(candidate) is None:
            raise ConfigurationError("invalid_decision_model")
        return candidate
    return DEFAULT_MODEL


def model_matches(returned_model: str, expected_model: str) -> bool:
    if returned_model == expected_model:
        return True
    pattern = rf"^{re.escape(expected_model)}(-\d{{8}})?$"
    return re.fullmatch(pattern, returned_model) is not None


class OpenRouterDecisionEvaluator:
    def __init__(self, credential: str, *, model: str | None = None, timeout: float = 10.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.model = resolve_decision_model(model)
        self.transport = JevTransport(credential, timeout=timeout, transport=transport)

    def prepare(self) -> "OpenRouterDecisionEvaluator":
        self.transport.prepare()
        return self

    async def aprepare(self) -> "OpenRouterDecisionEvaluator":
        await self.transport.aprepare()
        return self

    async def aevaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        payload = build_choice_request(check, context, model=self.model)
        data = await self.transport.apost(payload)
        return parse_choice_response(data, check, expected_model=self.model)

    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
        payload = build_choice_request(check, context, model=self.model)
        data = self.transport.post(payload)
        return parse_choice_response(data, check, expected_model=self.model)

    async def aclose(self) -> None:
        await self.transport.aclose()

    def close(self) -> None:
        self.transport.close()


JevEvaluator = OpenRouterDecisionEvaluator


def build_choice_request(check: CheckPolicy, context: EvaluationContext, *,
                         model: str = DEFAULT_MODEL) -> dict[str, object]:
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
        "model": model,
        "questions": {check.id: {"type": "choice", "instructions": instructions,
                                 "criteria": {"pass": passed, "violation": violated}}},
        "state": state,
        "provider": {"allow_fallbacks": False},
    }


def parse_choice_response(data: object, check: CheckPolicy, *,
                          expected_model: str = DEFAULT_MODEL) -> CheckResult:
    if not isinstance(data, Mapping) or not isinstance(data.get("model"), str) or (
        not model_matches(data["model"], expected_model)
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
        confidence=float(confidence), evaluator=data["model"], cost=float(cost) if cost is not None else None,
        input_tokens=input_tokens, output_tokens=output_tokens,
    )
