"""Sanitized public exception categories."""

import re


class AgentGuardError(Exception):
    """A guard failure with a content-free reason code."""

    def __init__(self, reason_code: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason_code):
            raise ValueError("invalid_reason_code")
        super().__init__(reason_code)
        self.reason_code = reason_code


class ConfigurationError(AgentGuardError):
    pass


class IntegrationError(AgentGuardError):
    pass


class PolicyViolationError(AgentGuardError):
    pass


class InconclusiveError(AgentGuardError):
    pass


class EvaluationError(AgentGuardError):
    pass
