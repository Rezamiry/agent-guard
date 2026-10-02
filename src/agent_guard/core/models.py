"""Immutable public core models and validation."""

import re
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite


def _valid_identity(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value))


def _valid_evaluator_identity(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", value))


class Boundary(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class CheckKind(StrEnum):
    PII = "pii"
    PROMPT_INJECTION = "prompt_injection"
    CONTENT_SAFETY = "content_safety"
    CUSTOM = "custom"
    RELEVANCE = "relevance"
    GROUNDEDNESS = "groundedness"


class Outcome(StrEnum):
    PASS = "pass"
    VIOLATION = "violation"
    INCONCLUSIVE = "inconclusive"
    EVALUATION_ERROR = "evaluation_error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class CheckPolicy:
    id: str
    kind: CheckKind
    boundary: Boundary
    required: bool = True
    minimum_confidence: float | None = None
    criteria: str | None = None
    enabled: bool = True
    criteria_revision: str = "v1"

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CheckKind) or not isinstance(self.boundary, Boundary):
            raise ValueError("invalid_check_scope")  # noqa: TRY004 - stable settings error
        if not isinstance(self.required, bool):
            raise ValueError("invalid_required_setting")  # noqa: TRY004 - stable settings error
        if not isinstance(self.enabled, bool):
            raise ValueError("invalid_enabled_setting")  # noqa: TRY004 - stable settings error
        if not _valid_identity(self.id):
            raise ValueError("check_identity_required")
        if self.kind in (CheckKind.RELEVANCE, CheckKind.GROUNDEDNESS) and self.boundary != Boundary.OUTPUT:
            raise ValueError("invalid_check_boundary")
        if self.kind == CheckKind.PROMPT_INJECTION and self.boundary != Boundary.INPUT:
            raise ValueError("invalid_check_boundary")
        if self.minimum_confidence is not None and (
            self.kind == CheckKind.PII
            or isinstance(self.minimum_confidence, bool)
            or not isfinite(self.minimum_confidence)
            or not 0 <= self.minimum_confidence <= 1
        ):
            raise ValueError("invalid_confidence_minimum")
        if self.criteria is not None and (not isinstance(self.criteria, str) or not self.criteria.strip()):
            raise ValueError("invalid_criteria")
        if not _valid_identity(self.criteria_revision):
            raise ValueError("invalid_criteria_revision")
        if self.kind == CheckKind.CUSTOM and self.criteria is None:
            raise ValueError("custom_criteria_required")


def _default_checks() -> tuple[CheckPolicy, ...]:
    return (
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT),
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT),
    )


@dataclass(frozen=True)
class PolicySet:
    checks: tuple[CheckPolicy, ...] = field(default_factory=_default_checks)
    evidence_required: bool = False
    id: str = "default-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.checks, tuple) or any(
            not isinstance(check, CheckPolicy) for check in self.checks
        ):
            raise ValueError("invalid_checks")
        if not isinstance(self.evidence_required, bool):
            raise ValueError("invalid_evidence_setting")  # noqa: TRY004 - stable settings error
        if not _valid_identity(self.id):
            raise ValueError("policy_identity_required")
        identities = [check.id for check in self.checks]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate_check_identity")
        boundaries = {check.boundary for check in self.checks if check.enabled}
        for boundary in boundaries:
            if not any(check.enabled and check.kind == CheckKind.PII and
                       check.boundary == boundary for check in self.checks):
                raise ValueError("local_pii_required_for_boundary")

    @property
    def settings_id(self) -> str:
        from .policy import settings_identity

        return settings_identity(self)


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    boundary: Boundary
    outcome: Outcome
    required: bool = True
    reason_code: str = ""
    confidence: float | None = None
    elapsed_seconds: float | None = None
    evaluator: str | None = None
    error_category: str | None = None
    cost: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.boundary, Boundary) or not isinstance(self.outcome, Outcome):
            raise ValueError("invalid_result_scope_or_outcome")  # noqa: TRY004 - stable settings error
        if not isinstance(self.required, bool):
            raise ValueError("invalid_required_setting")  # noqa: TRY004 - stable settings error
        if not _valid_identity(self.check_id):
            raise ValueError("invalid_check_identity")
        if self.reason_code and not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", self.reason_code):
            raise ValueError("invalid_reason_code")
        if self.confidence is not None and (not isfinite(self.confidence) or not 0 <= self.confidence <= 1):
            raise ValueError("invalid_confidence")
        if self.elapsed_seconds is not None and (not isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0):
            raise ValueError("invalid_elapsed_time")
        if self.evaluator is not None and not _valid_evaluator_identity(self.evaluator):
            raise ValueError("invalid_evaluator_identity")
        if self.error_category is not None and not re.fullmatch(
            r"[a-z][a-z0-9_]{0,127}", self.error_category
        ):
            raise ValueError("invalid_error_category")
        if self.cost is not None and (not isfinite(self.cost) or self.cost < 0):
            raise ValueError("invalid_cost")
        for count in (self.input_tokens, self.output_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError("invalid_usage")


@dataclass(frozen=True)
class BoundaryDecision:
    allowed: bool
    results: tuple[CheckResult, ...]
    reason_code: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool) or not isinstance(self.results, tuple) or any(
            not isinstance(result, CheckResult) for result in self.results
        ):
            raise ValueError("invalid_boundary_decision")
        if self.reason_code and not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", self.reason_code):
            raise ValueError("invalid_decision_reason")


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    text: str
    generation_id: str

    def __post_init__(self) -> None:
        if not _valid_identity(self.id) or not _valid_identity(self.generation_id):
            raise ValueError("evidence_identity_required")
        if not isinstance(self.text, str):
            raise ValueError("evidence_text_required")  # noqa: TRY004 - stable settings error


@dataclass(frozen=True)
class EvaluationContext:
    request_id: str
    current_request: str
    messages: tuple[object, ...] = ()
    candidate_answer: str | None = None
    evidence: tuple[EvidenceItem, ...] = ()
    generation_id: str | None = None
    tool_descriptions: tuple[str, ...] = ()
    tool_arguments: tuple[object, ...] = ()
    current_request_in_messages: bool = False

    def __post_init__(self) -> None:
        if not _valid_identity(self.request_id):
            raise ValueError("request_identity_required")
        if self.generation_id is not None and not _valid_identity(self.generation_id):
            raise ValueError("generation_identity_required")
        if not isinstance(self.current_request, str) or (
            self.candidate_answer is not None and not isinstance(self.candidate_answer, str)
        ):
            raise ValueError("invalid_context_text")
        if not isinstance(self.messages, tuple) or not isinstance(self.evidence, tuple) or (
            not isinstance(self.tool_descriptions, tuple) or not isinstance(self.tool_arguments, tuple)
        ) or any(
            not isinstance(item, EvidenceItem) for item in self.evidence
        ):
            raise ValueError("invalid_context_collection")
        if not isinstance(self.current_request_in_messages, bool):
            raise ValueError("invalid_request_location")  # noqa: TRY004 - stable settings error
        identities = [item.id for item in self.evidence]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate_evidence_identity")
