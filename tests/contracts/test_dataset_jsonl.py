import json
from pathlib import Path

from agent_guard.core.models import Outcome
from agent_guard.evaluation.dataset import DatasetLineError, SavedExample, read_jsonl


def test_jsonl_keeps_valid_records_around_sanitized_line_errors(tmp_path: Path) -> None:
    path = tmp_path / "saved.jsonl"
    first = {"schema_version": 1, "example_id": "e1", "request": "hello",
             "candidate_answer": "safe", "labels": [
                 {"policy_id": "p1", "boundary": "output", "outcome": "pass"},
             ]}
    later = {"schema_version": 1, "example_id": "e2", "request": "next",
             "candidate_answer": "safe"}
    path.write_text("\n".join((json.dumps(first), "{secret@example.com", json.dumps(first),
                               json.dumps(later))) + "\n", encoding="utf-8")
    rows = read_jsonl(path)
    assert len(rows) == 4
    assert isinstance(rows[0], SavedExample)
    assert rows[0].labels[0].outcome == Outcome.PASS
    assert isinstance(rows[1], DatasetLineError)
    assert isinstance(rows[2], DatasetLineError)
    assert isinstance(rows[3], SavedExample)
    assert rows[3].example_id == "e2"
    assert "secret@example.com" not in str(rows[1:3])


def test_duplicate_scoped_label_and_oversized_context_are_per_line_errors(tmp_path: Path) -> None:
    path = tmp_path / "saved.jsonl"
    duplicate = {"schema_version": 1, "example_id": "e1", "request": "hello",
                 "candidate_answer": "safe", "labels": [
                     {"policy_id": "p1", "boundary": "output", "outcome": "pass"},
                     {"policy_id": "p1", "boundary": "output", "outcome": "violation"},
                 ]}
    oversized = {"schema_version": 1, "example_id": "e2", "request": "x" * 100_001,
                 "candidate_answer": "safe"}
    path.write_text(json.dumps(duplicate) + "\n" + json.dumps(oversized) + "\n",
                    encoding="utf-8")
    assert all(isinstance(row, DatasetLineError) for row in read_jsonl(path))


def test_utf8_version_and_boundary_scoped_labels_with_optional_evidence(tmp_path: Path) -> None:
    path = tmp_path / "saved.jsonl"
    valid = {
        "schema_version": 1, "example_id": "e3", "request": "Résumé",
        "candidate_answer": "Safe", "generation_id": "gen",
        "evidence": [{"id": "source", "text": "Known fact", "generation_id": "gen"}],
        "labels": [
            {"policy_id": "p1", "boundary": "input", "outcome": "pass"},
            {"policy_id": "p1", "boundary": "output", "outcome": "violation"},
        ],
    }
    wrong_version = {**valid, "example_id": "e4", "schema_version": 2}
    path.write_bytes(json.dumps(valid, ensure_ascii=False).encode("utf-8") + b"\n"
                     + b"\xff\n" + json.dumps(wrong_version).encode("utf-8") + b"\n")
    rows = read_jsonl(path)
    assert isinstance(rows[0], SavedExample)
    assert rows[0].context.current_request == "Résumé"
    assert rows[0].context.evidence[0].id == "source"
    assert {(label.policy_id, label.boundary.value) for label in rows[0].labels} == {
        ("p1", "input"), ("p1", "output"),
    }
    assert isinstance(rows[1], DatasetLineError)
    assert isinstance(rows[2], DatasetLineError)
