"""Policy authoring and non-secret settings identity."""

from dataclasses import FrozenInstanceError

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, CheckResult, Guard, Outcome, PolicySet
from agent_guard.checks.semantic import normalize_judgment
from agent_guard.core.errors import ConfigurationError
from agent_guard.core.policy import settings_identity


def test_default_local_only_policy_is_immutable_and_needs_no_remote_evaluator() -> None:
    policy = PolicySet()
    assert {(item.kind, item.boundary, item.required) for item in policy.checks} == {
        (CheckKind.PII, Boundary.INPUT, True),
        (CheckKind.PII, Boundary.OUTPUT, True),
    }
    with pytest.raises(FrozenInstanceError):
        policy.id = "changed"  # type: ignore[misc]

    class Detector:
        def detect(self, text: str) -> bool:
            return False

    Guard(policy, detector=Detector()).prepare()


def test_nonsecret_settings_identity_is_stable_and_distinguishes_changes() -> None:
    base = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT,
                    criteria="Never expose secret@example.com"),
    ), id="policy-v1")
    same = PolicySet(checks=base.checks, id="policy-v1")
    different_required = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT, required=False,
                    criteria="Never expose secret@example.com"),
    ), id="policy-v1")
    different_revision = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT,
                    criteria="Never expose secret@example.com", criteria_revision="v2"),
    ), id="policy-v1")
    identity = settings_identity(base)
    assert identity == settings_identity(same)
    assert identity != settings_identity(different_required)
    assert identity != settings_identity(different_revision)
    assert "secret@example.com" not in identity


def test_invalid_criterion_revision_and_missing_enabled_dependency_fail_locally() -> None:
    with pytest.raises(ValueError):
        CheckPolicy("custom", CheckKind.CUSTOM, Boundary.OUTPUT, criteria="Safe",
                    criteria_revision="secret@example.com")
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    class Detector:
        def detect(self, text: str) -> bool:
            return False

    with pytest.raises(ConfigurationError) as error:
        Guard(policy, detector=Detector()).prepare()
    assert error.value.reason_code == "evaluator_unavailable"


def test_valid_scope_and_confidence_equality_below_minimum() -> None:
    with pytest.raises(ValueError):
        CheckPolicy("invalid", CheckKind.RELEVANCE, Boundary.INPUT)
    check = CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT,
                        minimum_confidence=0.75)
    equal = CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.75)
    below = CheckResult(check.id, check.boundary, Outcome.PASS, confidence=0.74)
    assert normalize_judgment(check, equal).outcome == Outcome.PASS
    assert normalize_judgment(check, below).outcome == Outcome.INCONCLUSIVE


def test_missing_credential_fails_locally_without_provider_probe() -> None:
    pytest.importorskip("httpx")
    from agent_guard.providers.transport import JevTransport

    with pytest.raises(ConfigurationError) as error:
        JevTransport("")
    assert error.value.reason_code == "provider_credential_required"
