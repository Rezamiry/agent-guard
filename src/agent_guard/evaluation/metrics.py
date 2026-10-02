"""Per-policy and boundary classification metrics."""

from dataclasses import dataclass

from agent_guard.core.models import Boundary, Outcome


@dataclass(frozen=True)
class MetricRow:
    example_id: str
    policy_id: str
    boundary: Boundary
    predicted: Outcome
    reference: Outcome | None = None


def summarize(rows: tuple[MetricRow, ...], *, policy_id: str,
              boundary: Boundary) -> dict[str, object]:
    selected = tuple(row for row in rows if row.policy_id == policy_id and row.boundary == boundary)
    for row in selected:
        if row.reference is not None and row.reference not in (Outcome.PASS, Outcome.VIOLATION):
            raise ValueError("invalid_reference_label")
    counts = {outcome: sum(row.predicted == outcome for row in selected) for outcome in Outcome}
    classified = tuple(row for row in selected if row.reference is not None and
                       row.predicted in (Outcome.PASS, Outcome.VIOLATION))
    tp = sum(row.reference == Outcome.VIOLATION and row.predicted == Outcome.VIOLATION
             for row in classified)
    fn = sum(row.reference == Outcome.VIOLATION and row.predicted == Outcome.PASS
             for row in classified)
    fp = sum(row.reference == Outcome.PASS and row.predicted == Outcome.VIOLATION
             for row in classified)
    tn = sum(row.reference == Outcome.PASS and row.predicted == Outcome.PASS
             for row in classified)
    total = len(selected)
    labeled = sum(row.reference is not None for row in selected)

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    return {
        "policy_id": policy_id,
        "boundary": boundary.value,
        "total": total,
        "labeled": labeled,
        "classified": len(classified),
        "pass": counts[Outcome.PASS],
        "violation": counts[Outcome.VIOLATION],
        "inconclusive": counts[Outcome.INCONCLUSIVE],
        "evaluation_error": counts[Outcome.EVALUATION_ERROR],
        "skipped": counts[Outcome.SKIPPED],
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": ratio(tp + tn, len(classified)),
        "accuracy_denominator": len(classified),
        "precision": ratio(tp, tp + fp),
        "precision_denominator": tp + fp,
        "recall": ratio(tp, tp + fn),
        "recall_denominator": tp + fn,
        "false_positive_rate": ratio(fp, fp + tn),
        "false_positive_rate_denominator": fp + tn,
        "labeled_coverage": ratio(labeled, total),
        "classified_coverage": ratio(len(classified), total),
    }
