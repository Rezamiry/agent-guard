import pytest

from agent_guard.core.content import extract_snapshot
from agent_guard.core.errors import IntegrationError


def test_snapshot_preserves_roles_parts_tool_keys_and_evidence() -> None:
    parts = extract_snapshot(
        [
            {"role": "system", "content": "Policy text"},
            {"role": "user", "content": [{"type": "text", "text": "First"}, {"type": "text", "text": "Second"}]},
        ],
        tool_descriptions=["lookup description"],
        tool_arguments=[{"secret@example.com": ["lookup"]}],
        evidence=["Evidence text"],
    )
    assert parts == (
        "Policy text", "First", "Second", "lookup description",
        "secret@example.com", "lookup", "Evidence text",
    )


def test_snapshot_rejects_opaque_and_multimodal_parts() -> None:
    with pytest.raises(IntegrationError):
        extract_snapshot([{"role": "user", "content": [{"type": "image", "data": "raw"}]}])
    with pytest.raises(IntegrationError):
        extract_snapshot([{"role": "user", "content": object()}])


def test_snapshot_rejects_unsupported_role_and_overflow() -> None:
    with pytest.raises(IntegrationError):
        extract_snapshot([{"role": "arbitrary", "content": "text"}])
    with pytest.raises(IntegrationError):
        extract_snapshot([{"role": "user", "content": "x" * 100_001}])


def test_snapshot_counts_tool_argument_keys() -> None:
    with pytest.raises(IntegrationError):
        extract_snapshot([], tool_arguments=[{"x" * 100_001: True}])


def test_all_supported_roles_and_inclusive_limits() -> None:
    roles = ("system", "developer", "user", "assistant", "tool")
    assert extract_snapshot([{"role": role, "content": role} for role in roles]) == roles
    assert extract_snapshot([{"role": "user", "content": "x" * 100_000}]) == (
        "x" * 100_000,
    )
    assert len(extract_snapshot([{"role": "user", "content": ""}] * 128)) == 128
    with pytest.raises(IntegrationError):
        extract_snapshot([{"role": "user", "content": ""}] * 129)
    assert len(extract_snapshot([], evidence=[""] * 64)) == 64
    with pytest.raises(IntegrationError):
        extract_snapshot([], evidence=[""] * 65)


def test_nested_argument_values_are_inspected_without_stringifying_non_text() -> None:
    assert extract_snapshot([], tool_arguments=[{"outer": [{"inner": "value"}, 42, False]}]) == (
        "outer", "inner", "value",
    )
    with pytest.raises(IntegrationError):
        extract_snapshot([], tool_arguments=[{"opaque": object()}])
