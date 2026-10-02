from agent_guard import Boundary, Outcome
from agent_guard.evaluation.metrics import MetricRow, summarize


def test_independent_seven_example_confusion_counts() -> None:
    rows = (
        MetricRow("tp", "p1", Boundary.OUTPUT, Outcome.VIOLATION, Outcome.VIOLATION),
        MetricRow("fn", "p1", Boundary.OUTPUT, Outcome.PASS, Outcome.VIOLATION),
        MetricRow("fp", "p1", Boundary.OUTPUT, Outcome.VIOLATION, Outcome.PASS),
        MetricRow("tn1", "p1", Boundary.OUTPUT, Outcome.PASS, Outcome.PASS),
        MetricRow("tn2", "p1", Boundary.OUTPUT, Outcome.PASS, Outcome.PASS),
        MetricRow("error", "p1", Boundary.OUTPUT, Outcome.EVALUATION_ERROR, Outcome.PASS),
        MetricRow("skip", "p1", Boundary.OUTPUT, Outcome.SKIPPED, Outcome.VIOLATION),
    )
    report = summarize(rows, policy_id="p1", boundary=Boundary.OUTPUT)
    assert (report["total"], report["classified"], report["evaluation_error"],
            report["skipped"]) == (7, 5, 1, 1)
    assert (report["tp"], report["fn"], report["fp"], report["tn"]) == (1, 1, 1, 2)
    assert report["accuracy"] == 3 / 5
    assert report["precision"] == 1 / 2
    assert report["recall"] == 1 / 2
    assert report["false_positive_rate"] == 1 / 3
    assert report["classified_coverage"] == 5 / 7


def test_undefined_ratios_are_unknown() -> None:
    report = summarize((), policy_id="p1", boundary=Boundary.OUTPUT)
    assert report["accuracy"] is None
    assert report["precision"] is None
    assert report["recall"] is None
    assert report["false_positive_rate"] is None
