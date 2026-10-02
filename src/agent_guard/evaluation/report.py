"""Sanitized saved-evaluation report formats."""

import csv
import io
import json
import re
from math import isfinite

from agent_guard.core.models import _valid_identity
from agent_guard.core.records import record_for
from agent_guard.evaluation.runner import OfflineResult


def json_report(results: tuple[OfflineResult, ...]) -> str:
    examples: list[dict[str, object]] = []
    for result in results:
        if not _valid_identity(result.policy_id) or (
            result.example_id is not None and not _valid_identity(result.example_id)
        ) or (
            result.settings_id is not None and not _valid_identity(result.settings_id)
        ):
            raise ValueError("invalid_report_identity")
        if result.error_category is not None and not re.fullmatch(
            r"[a-z][a-z0-9_]{0,127}", result.error_category
        ):
            raise ValueError("invalid_error_category")
        decision = result.output_decision
        examples.append({
            "example_id": result.example_id,
            "line_number": result.line_number,
            "policy_id": result.policy_id,
            "settings_id": result.settings_id,
            "decision": "error" if decision is None else "allow" if decision.allowed else "block",
            "reason_code": result.error_category if decision is None else decision.reason_code,
            "checks": [] if decision is None else [
                record_for(check, policy_id=result.policy_id,
                           settings_id=result.settings_id) for check in decision.results
            ],
        })
    return json.dumps({"schema_version": 1, "examples": examples}, separators=(",", ":"))


def csv_summary(metrics: dict[str, object]) -> str:
    fields = (
        "policy_id", "boundary", "total", "labeled", "classified", "pass", "violation",
        "inconclusive", "evaluation_error", "skipped", "tp", "fp", "tn", "fn",
        "accuracy", "accuracy_denominator", "precision", "precision_denominator",
        "recall", "recall_denominator", "false_positive_rate",
        "false_positive_rate_denominator", "labeled_coverage", "classified_coverage",
    )
    if not _valid_identity(metrics.get("policy_id")) or metrics.get("boundary") not in (
        "input", "output",
    ):
        raise ValueError("invalid_summary_identity")
    for field in fields[2:]:
        value = metrics.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (
            not isfinite(value) or value < 0
        ):
            raise ValueError("invalid_summary_value")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerow({field: metrics.get(field) for field in fields})
    return output.getvalue()


def compare_results(left: tuple[OfflineResult, ...],
                    right: tuple[OfflineResult, ...]) -> dict[str, object]:
    def counts(results: tuple[OfflineResult, ...]) -> dict[str, int]:
        totals = {"allow": 0, "block": 0, "error": 0}
        for result in results:
            if result.output_decision is None:
                totals["error"] += 1
            elif result.output_decision.allowed:
                totals["allow"] += 1
            else:
                totals["block"] += 1
        return totals

    for side in (left, right):
        if any(not _valid_identity(result.policy_id) or (
            result.example_id is not None and not _valid_identity(result.example_id)
        ) or (
            result.settings_id is not None and not _valid_identity(result.settings_id)
        ) for result in side):
            raise ValueError("invalid_comparison_identity")
        if len({result.policy_id for result in side}) > 1:
            raise ValueError("comparison_policy_mismatch")
        example_ids = [result.example_id for result in side if result.example_id is not None]
        if len(example_ids) != len(set(example_ids)):
            raise ValueError("duplicate_comparison_example")
    if tuple(result.example_id for result in left) != tuple(result.example_id for result in right):
        raise ValueError("comparison_examples_mismatch")
    changed: list[str] = []
    for result, other in zip(left, right, strict=True):
        if result.example_id is None:
            continue
        left_allowed = None if result.output_decision is None else result.output_decision.allowed
        right_allowed = None if other.output_decision is None else other.output_decision.allowed
        if left_allowed != right_allowed:
            changed.append(result.example_id)
    return {
        "schema_version": 1,
        "left_policy_id": left[0].policy_id if left else None,
        "right_policy_id": right[0].policy_id if right else None,
        "left_settings_id": left[0].settings_id if left else None,
        "right_settings_id": right[0].settings_id if right else None,
        "changed_example_ids": changed,
        "changed_count": len(changed),
        "left_counts": counts(left),
        "right_counts": counts(right),
    }
