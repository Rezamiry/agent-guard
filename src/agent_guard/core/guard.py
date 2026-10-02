"""Prepared guard lifecycle and input/output operations."""

from dataclasses import replace
from typing import Protocol

from agent_guard.checks.semantic import normalize_judgment

from .content import extract_snapshot, validate_limits
from .decision import reduce_results
from .errors import (
    AgentGuardError,
    ConfigurationError,
    EvaluationError,
    InconclusiveError,
    IntegrationError,
    PolicyViolationError,
)
from .input import assembled_input_text, local_pii_preflight, request_already_counted
from .models import (
    Boundary,
    BoundaryDecision,
    CheckKind,
    CheckPolicy,
    CheckResult,
    EvaluationContext,
    EvidenceItem,
    Outcome,
    PolicySet,
)


class LocalDetector(Protocol):
    def detect(self, text: str) -> bool: ...


class SemanticEvaluator(Protocol):
    def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> Outcome | CheckResult: ...


class Guard:
    def __init__(self, policy: PolicySet | None = None, *, detector: LocalDetector | None = None,
                 evaluator: SemanticEvaluator | None = None) -> None:
        self.policy = policy or PolicySet()
        self.detector = detector
        self.evaluator = evaluator
        self._prepared = False
        self._closed = False

    def prepare(self) -> "Guard":
        self._validate_preparation()
        try:
            for resource in self._enabled_resources():
                prepare = getattr(resource, "prepare", None)
                if callable(prepare):
                    prepare()
        except AgentGuardError:
            raise
        except Exception:  # noqa: BLE001 - setup internals may include secrets
            raise ConfigurationError("dependency_prepare_failed") from None
        self._prepared = True
        return self

    def _validate_preparation(self) -> None:
        if self._closed:
            raise ConfigurationError("guard_closed")
        kinds = {check.kind for check in self.policy.checks if check.enabled}
        if CheckKind.PII in kinds and self.detector is None:
            raise ConfigurationError("local_pii_unavailable")
        if any(kind != CheckKind.PII for kind in kinds) and self.evaluator is None:
            raise ConfigurationError("evaluator_unavailable")

    def _enabled_resources(self) -> tuple[LocalDetector | SemanticEvaluator, ...]:
        kinds = {check.kind for check in self.policy.checks if check.enabled}
        resources: list[LocalDetector | SemanticEvaluator] = []
        if CheckKind.PII in kinds and self.detector is not None:
            resources.append(self.detector)
        if any(kind != CheckKind.PII for kind in kinds) and self.evaluator is not None:
            resources.append(self.evaluator)
        return tuple(resources)

    def close(self) -> None:
        for resource in self._enabled_resources():
            close = getattr(resource, "close", None)
            if callable(close):
                close()
        self._closed = True
        self._prepared = False

    async def aprepare(self) -> "Guard":
        self._validate_preparation()
        try:
            for resource in self._enabled_resources():
                async_prepare = getattr(resource, "aprepare", None)
                if callable(async_prepare):
                    await async_prepare()
                else:
                    prepare = getattr(resource, "prepare", None)
                    if callable(prepare):
                        prepare()
        except AgentGuardError:
            raise
        except Exception:  # noqa: BLE001 - setup internals may include secrets
            raise ConfigurationError("dependency_prepare_failed") from None
        self._prepared = True
        return self

    async def aclose(self) -> None:
        for resource in self._enabled_resources():
            async_close = getattr(resource, "aclose", None)
            if callable(async_close):
                await async_close()
            else:
                close = getattr(resource, "close", None)
                if callable(close):
                    close()
        self._closed = True
        self._prepared = False

    def evaluate_input(self, context: EvaluationContext) -> BoundaryDecision:
        return self._evaluate(context, Boundary.INPUT)

    async def aevaluate_input(self, context: EvaluationContext) -> BoundaryDecision:
        return await self._aevaluate(context, Boundary.INPUT)

    async def aenforce_input(self, context: EvaluationContext) -> BoundaryDecision:
        decision = await self.aevaluate_input(context)
        self._raise_if_blocked(decision)
        return decision

    def evaluate_output(self, context: EvaluationContext) -> BoundaryDecision:
        return self._evaluate(context, Boundary.OUTPUT)

    async def aevaluate_output(self, context: EvaluationContext) -> BoundaryDecision:
        return await self._aevaluate(context, Boundary.OUTPUT)

    async def aenforce_output(self, context: EvaluationContext) -> str:
        decision = await self.aevaluate_output(context)
        self._raise_if_blocked(decision)
        assert context.candidate_answer is not None
        return context.candidate_answer

    def enforce_input(self, context: EvaluationContext) -> BoundaryDecision:
        decision = self.evaluate_input(context)
        self._raise_if_blocked(decision)
        return decision

    def enforce_output(self, context: EvaluationContext) -> str:
        decision = self.evaluate_output(context)
        self._raise_if_blocked(decision)
        assert context.candidate_answer is not None
        return context.candidate_answer

    def _evaluate(self, context: EvaluationContext, boundary: Boundary) -> BoundaryDecision:
        if not self._prepared or self._closed:
            raise ConfigurationError("guard_not_prepared")
        if boundary == Boundary.OUTPUT and context.candidate_answer is None:
            raise ConfigurationError("candidate_answer_required")
        checks = tuple(check for check in self.policy.checks if check.enabled and
                       check.boundary == boundary)
        evidence_items, inspection_text = self._snapshot(context, boundary, checks)
        evidence = tuple(item.text for item in evidence_items)
        local_results = tuple(self._check_pii(check, inspection_text) for check in checks
                              if check.kind == CheckKind.PII)
        if any(result.required and result.outcome != Outcome.PASS for result in local_results):
            skipped = tuple(CheckResult(check.id, boundary, Outcome.SKIPPED, check.required,
                                        "privacy_preflight_blocked") for check in checks
                            if check.kind != CheckKind.PII)
            return reduce_results(local_results + skipped)
        scoped_context = replace(context, evidence=evidence_items)
        semantic_results: list[CheckResult] = []
        required_failed = False
        for check in checks:
            if check.kind == CheckKind.PII:
                continue
            if required_failed:
                semantic_results.append(CheckResult(check.id, boundary, Outcome.SKIPPED,
                                                    check.required, "prior_required_failure"))
                continue
            result = self._check_semantic(check, scoped_context, bool(evidence))
            semantic_results.append(result)
            required_failed = (
                result.required and result.outcome not in (Outcome.PASS, Outcome.SKIPPED)
            ) or (
                result.outcome == Outcome.SKIPPED and check.kind == CheckKind.GROUNDEDNESS
                and boundary == Boundary.OUTPUT and self.policy.evidence_required
            )
        return reduce_results(local_results + tuple(semantic_results),
                              evidence_required=self.policy.evidence_required and boundary == Boundary.OUTPUT,
                              evidence_present=bool(evidence))

    async def _aevaluate(self, context: EvaluationContext, boundary: Boundary) -> BoundaryDecision:
        if not self._prepared or self._closed:
            raise ConfigurationError("guard_not_prepared")
        if boundary == Boundary.OUTPUT and context.candidate_answer is None:
            raise ConfigurationError("candidate_answer_required")
        checks = tuple(check for check in self.policy.checks if check.enabled and
                       check.boundary == boundary)
        evidence_items, inspection_text = self._snapshot(context, boundary, checks)
        evidence = tuple(item.text for item in evidence_items)
        local_results = tuple(self._check_pii(check, inspection_text) for check in checks
                              if check.kind == CheckKind.PII)
        if any(result.required and result.outcome != Outcome.PASS for result in local_results):
            skipped = tuple(CheckResult(check.id, boundary, Outcome.SKIPPED, check.required,
                                        "privacy_preflight_blocked") for check in checks
                            if check.kind != CheckKind.PII)
            return reduce_results(local_results + skipped)
        scoped_context = replace(context, evidence=evidence_items)
        semantic_results: list[CheckResult] = []
        required_failed = False
        for check in checks:
            if check.kind == CheckKind.PII:
                continue
            if required_failed:
                semantic_results.append(CheckResult(check.id, boundary, Outcome.SKIPPED,
                                                    check.required, "prior_required_failure"))
                continue
            result = await self._acheck_semantic(check, scoped_context, bool(evidence))
            semantic_results.append(result)
            required_failed = (
                result.required and result.outcome not in (Outcome.PASS, Outcome.SKIPPED)
            ) or (
                result.outcome == Outcome.SKIPPED and check.kind == CheckKind.GROUNDEDNESS
                and boundary == Boundary.OUTPUT and self.policy.evidence_required
            )
        return reduce_results(local_results + tuple(semantic_results),
                              evidence_required=self.policy.evidence_required and boundary == Boundary.OUTPUT,
                              evidence_present=bool(evidence))

    def _check_pii(self, check: CheckPolicy, text: str) -> CheckResult:
        assert self.detector is not None
        return local_pii_preflight(check, text, self.detector)

    @staticmethod
    def _snapshot(context: EvaluationContext, boundary: Boundary,
                  checks: tuple[CheckPolicy, ...]) -> tuple[tuple[EvidenceItem, ...], str]:
        if boundary == Boundary.INPUT:
            return context.evidence, assembled_input_text(context, checks)
        validate_limits(messages=len(context.messages), evidence_items=len(context.evidence))
        evidence_items = tuple(item for item in context.evidence if
                               context.generation_id is not None and
                               item.generation_id == context.generation_id)
        parts = extract_snapshot(
            context.messages, evidence=tuple(item.text for item in evidence_items),
            tool_descriptions=context.tool_descriptions,
            tool_arguments=context.tool_arguments,
            answer=context.candidate_answer,
        )
        inspection_parts = (
            (context.current_request,) + parts
            + tuple(check.criteria for check in checks if check.criteria is not None)
        )
        counted_parts = parts + tuple(check.criteria for check in checks if check.criteria is not None)
        if not request_already_counted(context):
            counted_parts = (context.current_request,) + counted_parts
        validate_limits(text="".join(counted_parts), messages=len(context.messages),
                        evidence_items=len(context.evidence))
        return evidence_items, Guard._inspection_text(inspection_parts)

    @staticmethod
    def _inspection_text(parts: tuple[str, ...]) -> str:
        if len(parts) <= 1:
            return parts[0] if parts else ""
        return "\n".join(parts) + "\n" + "".join(parts)

    def _check_semantic(self, check: CheckPolicy, context: EvaluationContext,
                        evidence_present: bool) -> CheckResult:
        if check.kind == CheckKind.GROUNDEDNESS and not evidence_present:
            return CheckResult(check.id, check.boundary, Outcome.SKIPPED,
                               check.required, "no_evidence")
        try:
            assert self.evaluator is not None
            evaluate = self.evaluator.evaluate
            judgment = evaluate(check, context)
            return normalize_judgment(check, judgment)
        except (ConfigurationError, IntegrationError):
            raise
        except EvaluationError as exc:
            return CheckResult(check.id, check.boundary, Outcome.EVALUATION_ERROR,
                               check.required, exc.reason_code, error_category=exc.reason_code)
        except Exception:  # noqa: BLE001 - provider failures become sanitized results
            return CheckResult(check.id, check.boundary, Outcome.EVALUATION_ERROR,
                               check.required, "evaluator_error", error_category="evaluator_error")

    async def _acheck_semantic(self, check: CheckPolicy, context: EvaluationContext,
                              evidence_present: bool) -> CheckResult:
        if check.kind == CheckKind.GROUNDEDNESS and not evidence_present:
            return CheckResult(check.id, check.boundary, Outcome.SKIPPED,
                               check.required, "no_evidence")
        try:
            assert self.evaluator is not None
            async_evaluate = getattr(self.evaluator, "aevaluate", None)
            if callable(async_evaluate):
                judgment = await async_evaluate(check, context)
            else:
                judgment = self.evaluator.evaluate(check, context)
            return normalize_judgment(check, judgment)
        except (ConfigurationError, IntegrationError):
            raise
        except EvaluationError as exc:
            return CheckResult(check.id, check.boundary, Outcome.EVALUATION_ERROR,
                               check.required, exc.reason_code, error_category=exc.reason_code)
        except Exception:  # noqa: BLE001 - provider failures become sanitized results
            return CheckResult(check.id, check.boundary, Outcome.EVALUATION_ERROR,
                               check.required, "evaluator_error", error_category="evaluator_error")

    @staticmethod
    def _raise_if_blocked(decision: BoundaryDecision) -> None:
        if decision.allowed:
            return
        outcome = next((result.outcome for result in decision.results
                        if result.required and result.reason_code == decision.reason_code), None)
        if outcome == Outcome.VIOLATION:
            raise PolicyViolationError(decision.reason_code)
        if outcome == Outcome.EVALUATION_ERROR:
            raise EvaluationError(decision.reason_code)
        raise InconclusiveError(decision.reason_code)
