"""Versioned saved-example JSONL import."""

import json
from dataclasses import dataclass
from pathlib import Path

from agent_guard.core.content import extract_snapshot, validate_limits
from agent_guard.core.errors import IntegrationError
from agent_guard.core.models import (
    Boundary,
    EvaluationContext,
    EvidenceItem,
    Outcome,
    _valid_identity,
)


@dataclass(frozen=True)
class SavedLabel:
    policy_id: str
    boundary: Boundary
    outcome: Outcome


@dataclass(frozen=True)
class SavedExample:
    example_id: str
    context: EvaluationContext
    labels: tuple[SavedLabel, ...] = ()

    def __post_init__(self) -> None:
        if not _valid_identity(self.example_id) or self.example_id != self.context.request_id:
            raise ValueError("invalid_example_identity")


@dataclass(frozen=True)
class DatasetLineError:
    line_number: int
    reason_code: str


def read_jsonl(path: str | Path) -> tuple[SavedExample | DatasetLineError, ...]:
    records: list[SavedExample | DatasetLineError] = []
    seen: set[str] = set()
    with Path(path).open("rb") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if len(raw_line) > 1_000_000:
                records.append(DatasetLineError(line_number, "record_oversized"))
                continue
            try:
                value = json.loads(raw_line.decode("utf-8"))
                record = _parse_record(value)
                if record.example_id in seen:
                    raise ValueError("duplicate_example")
                seen.add(record.example_id)
                records.append(record)
            except (UnicodeError, json.JSONDecodeError, TypeError, ValueError,
                    KeyError, IntegrationError):
                records.append(DatasetLineError(line_number, "invalid_record"))
    return tuple(records)


def _parse_record(value: object) -> SavedExample:
    if not isinstance(value, dict) or set(value) - {
        "schema_version", "example_id", "request", "candidate_answer", "messages",
        "evidence", "generation_id", "labels",
    }:
        raise ValueError("invalid_record_shape")
    if (type(value.get("schema_version")) is not int or value["schema_version"] != 1
        or not _valid_identity(value.get("example_id"))
        or not isinstance(value.get("request"), str)
        or not isinstance(value.get("candidate_answer"), str)):
        raise ValueError("invalid_record_fields")
    messages = value.get("messages", [])
    evidence_data = value.get("evidence", [])
    label_data = value.get("labels", [])
    if not isinstance(messages, list) or not isinstance(evidence_data, list) or not isinstance(label_data, list):
        raise ValueError("invalid_record_collections")  # noqa: TRY004 - stable record error
    evidence: list[EvidenceItem] = []
    for item in evidence_data:
        if not isinstance(item, dict) or set(item) != {"id", "text", "generation_id"}:
            raise ValueError("invalid_evidence")
        evidence.append(EvidenceItem(item["id"], item["text"], item["generation_id"]))
    labels: list[SavedLabel] = []
    label_keys: set[tuple[str, Boundary]] = set()
    for item in label_data:
        if not isinstance(item, dict) or set(item) != {"policy_id", "boundary", "outcome"}:
            raise ValueError("invalid_label")
        if not _valid_identity(item["policy_id"]) or item["outcome"] not in ("pass", "violation"):
            raise ValueError("invalid_label")
        boundary = Boundary(item["boundary"])
        key = (item["policy_id"], boundary)
        if key in label_keys:
            raise ValueError("duplicate_label")
        label_keys.add(key)
        labels.append(SavedLabel(item["policy_id"], boundary, Outcome(item["outcome"])))
    context = EvaluationContext(
        value["example_id"], value["request"], tuple(messages), value["candidate_answer"],
        tuple(evidence), value.get("generation_id"),
    )
    parts = extract_snapshot(context.messages, evidence=tuple(item.text for item in evidence),
                             answer=context.candidate_answer)
    validate_limits(text=context.current_request + "".join(parts),
                    messages=len(context.messages), evidence_items=len(evidence))
    return SavedExample(value["example_id"], context, tuple(labels))
