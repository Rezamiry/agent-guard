import importlib.util
import socket

import pytest

from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.core.errors import ConfigurationError


def test_missing_model_is_reported_locally_without_download(monkeypatch: pytest.MonkeyPatch) -> None:
    import spacy

    def forbid_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("local detector attempted a network connection")

    monkeypatch.setattr(spacy.util, "is_package", lambda name: False)
    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    with pytest.raises(ConfigurationError) as error:
        LocalPIIDetector().prepare()
    assert error.value.reason_code == "pii_model_unavailable"


def test_preset_is_explicit_and_rejects_unknown_language() -> None:
    with pytest.raises(ConfigurationError):
        LocalPIIDetector(language="fr")


def test_pinned_model_detects_curated_categories_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    if importlib.util.find_spec("en_core_web_lg") is None:
        pytest.skip("model asset not provisioned into project environment")

    def forbid_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("local detector attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    detector = LocalPIIDetector()
    detector.prepare()
    try:
        for text in (
            "Jane Doe", "jane@example.com", "+1 212-555-0123",
            "+1 416-555-0123", "+44 20 7946 0958",
            "4111 1111 1111 1111", "SSN 987-65-4321",
        ):
            assert detector.detect(text), text
        assert not detector.detect("Summarize the report")
    finally:
        detector.close()
