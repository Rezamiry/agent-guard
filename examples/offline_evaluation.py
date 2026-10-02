"""Run fixed saved answers without generating replacement answers."""

from pathlib import Path

from agent_guard import Boundary, Guard
from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.evaluation.dataset import SavedExample, read_jsonl
from agent_guard.evaluation.metrics import MetricRow, summarize
from agent_guard.evaluation.report import csv_summary, json_report
from agent_guard.evaluation.runner import run_saved


def main() -> None:
    dataset = read_jsonl(Path(__file__).parent / "data" / "saved.jsonl")
    guard = Guard(detector=LocalPIIDetector()).prepare()
    try:
        results = run_saved(guard, dataset)
        rows: list[MetricRow] = []
        for source, result in zip(dataset, results, strict=True):
            if not isinstance(source, SavedExample) or result.output_decision is None:
                continue
            label = next((label for label in source.labels if label.policy_id == guard.policy.id
                          and label.boundary == Boundary.OUTPUT), None)
            rows.append(MetricRow(source.example_id, guard.policy.id, Boundary.OUTPUT,
                                  result.output_decision.results[0].outcome,
                                  label.outcome if label else None))
        print(json_report(results))
        print(csv_summary(summarize(tuple(rows), policy_id=guard.policy.id,
                                    boundary=Boundary.OUTPUT)), end="")
    finally:
        guard.close()


if __name__ == "__main__":
    main()
