import pytest

from agent_guard.core.errors import (
    ConfigurationError,
    EvaluationError,
    InconclusiveError,
    IntegrationError,
    PolicyViolationError,
)


def test_exception_reason_rejects_content_and_preserves_category() -> None:
    assert str(ConfigurationError("local_pii_unavailable")) == "local_pii_unavailable"
    assert isinstance(IntegrationError("unsupported_content"), IntegrationError)
    with pytest.raises(ValueError):
        IntegrationError("secret@example.com")


@pytest.mark.parametrize("error_type", [
    ConfigurationError, IntegrationError, PolicyViolationError, InconclusiveError,
    EvaluationError,
])
def test_all_guard_errors_use_only_safe_reason_codes(error_type: type[Exception]) -> None:
    assert str(error_type("provider_timeout")) == "provider_timeout"
    with pytest.raises(ValueError):
        error_type("credential=top-secret")
