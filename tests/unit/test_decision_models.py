import httpx
import pytest

from agent_guard.core.errors import ConfigurationError
from agent_guard.core.models import Boundary, CheckKind, CheckPolicy, EvaluationContext, Outcome
from agent_guard.providers.jev import (
    DEFAULT_MODEL,
    FALLBACK_ENV_MODEL,
    PRIMARY_ENV_MODEL,
    SUPPORTED_DECISION_MODELS,
    JevEvaluator,
    OpenRouterDecisionEvaluator,
    model_matches,
    resolve_decision_model,
)

CHECK = CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT)


def test_default_model_is_jev_1_13(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PRIMARY_ENV_MODEL, raising=False)
    monkeypatch.delenv(FALLBACK_ENV_MODEL, raising=False)
    assert resolve_decision_model() == DEFAULT_MODEL
    assert DEFAULT_MODEL == "typesafe/jev-1.13"


def test_primary_env_var_configures_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRIMARY_ENV_MODEL, "google/gemini-decision-1")
    monkeypatch.delenv(FALLBACK_ENV_MODEL, raising=False)
    assert resolve_decision_model() == "google/gemini-decision-1"


def test_fallback_env_var_configures_model_when_primary_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PRIMARY_ENV_MODEL, raising=False)
    monkeypatch.setenv(FALLBACK_ENV_MODEL, "perplexity/decider-v1.2")
    assert resolve_decision_model() == "perplexity/decider-v1.2"


def test_primary_env_var_takes_precedence_over_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRIMARY_ENV_MODEL, "google/gemini-decision-1")
    monkeypatch.setenv(FALLBACK_ENV_MODEL, "perplexity/decider-v1.2")
    assert resolve_decision_model() == "google/gemini-decision-1"


def test_constructor_parameter_overrides_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRIMARY_ENV_MODEL, "google/gemini-decision-1")
    monkeypatch.setenv(FALLBACK_ENV_MODEL, "perplexity/decider-v1.2")
    assert resolve_decision_model("cloudflare/clef-flash") == "cloudflare/clef-flash"


@pytest.mark.parametrize("invalid_model", [
    "",
    "   ",
    "invalid",
    "invalid model",
    "vendor/",
    "/model",
    "vendor/model/extra",
])
def test_invalid_model_format_raises_configuration_error(invalid_model: str) -> None:
    with pytest.raises(ConfigurationError) as exc:
        resolve_decision_model(invalid_model)
    assert exc.value.reason_code == "invalid_decision_model"


def test_invalid_env_var_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRIMARY_ENV_MODEL, "   ")
    with pytest.raises(ConfigurationError) as exc:
        resolve_decision_model()
    assert exc.value.reason_code == "invalid_decision_model"


def test_model_matches_exact_and_snapshot() -> None:
    assert model_matches("typesafe/jev-1.13", "typesafe/jev-1.13")
    assert model_matches("typesafe/jev-1.13-20260917", "typesafe/jev-1.13")
    assert not model_matches("typesafe/jev-1.14", "typesafe/jev-1.13")
    assert not model_matches("typesafe/jev-1.13-beta", "typesafe/jev-1.13")

    assert model_matches("google/gemini-decision-1", "google/gemini-decision-1")
    assert model_matches("google/gemini-decision-1-20261115", "google/gemini-decision-1")
    assert not model_matches("google/gemini-decision-2", "google/gemini-decision-1")


def test_openrouter_evaluator_alias_and_model_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PRIMARY_ENV_MODEL, raising=False)
    evaluator = OpenRouterDecisionEvaluator("test_token")
    assert evaluator.model == DEFAULT_MODEL
    assert isinstance(evaluator, JevEvaluator)

    evaluator_custom = OpenRouterDecisionEvaluator("test_token", model="parallel/decisions-fast")
    assert evaluator_custom.model == "parallel/decisions-fast"


def test_evaluator_uses_configured_model_in_request_and_validates_response() -> None:
    recorded_model = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal recorded_model
        import json
        body = json.loads(request.content.decode("utf-8"))
        recorded_model = body.get("model")
        return httpx.Response(200, json={
            "model": "cloudflare/clef-flash-20261010",
            "answers": {"relevance": {"type": "choice", "choice": "pass", "confidence": 0.9}},
            "usage": {"input_tokens": 15, "output_tokens": 1, "cost": 0.0001},
        })

    evaluator = OpenRouterDecisionEvaluator("token", model="cloudflare/clef-flash",
                                           transport=httpx.MockTransport(handler)).prepare()
    try:
        context = EvaluationContext("req", "request", candidate_answer="answer")
        result = evaluator.evaluate(CHECK, context)
        assert recorded_model == "cloudflare/clef-flash"
        assert result.outcome == Outcome.PASS
        assert result.evaluator == "cloudflare/clef-flash-20261010"
        assert result.cost == 0.0001
    finally:
        evaluator.close()


def test_supported_decision_models_catalog_contains_expected_models() -> None:
    expected = {
        "typesafe/jev-1.13",
        "typesafe/jev-1.14",
        "google/gemini-decision-1",
        "perplexity/decider-v1.2",
        "perplexity/decider-flash-v1.3",
        "cloudflare/clef-flash",
        "parallel/decisions-fast",
        "nace-ai/drex-max",
        "liquid/d1",
        "openai/gpt-6-luna-decisions",
    }
    assert expected.issubset(set(SUPPORTED_DECISION_MODELS.keys()))
    for meta in SUPPORTED_DECISION_MODELS.values():
        assert "provider" in meta
        assert "modality" in meta
        assert "description" in meta
