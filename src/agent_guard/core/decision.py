"""Pure decision reducer."""

from .models import BoundaryDecision, CheckResult, Outcome


def reduce_results(results: tuple[CheckResult, ...], *, evidence_required: bool = False,
                   evidence_present: bool = True) -> BoundaryDecision:
    if evidence_required and not evidence_present:
        return BoundaryDecision(False, results, "evidence_required")
    for result in results:
        if result.required and result.outcome in (
            Outcome.VIOLATION,
            Outcome.INCONCLUSIVE,
            Outcome.EVALUATION_ERROR,
        ):
            return BoundaryDecision(False, results, result.reason_code or result.outcome.value)
    return BoundaryDecision(True, results, "allow")
