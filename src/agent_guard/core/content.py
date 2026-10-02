"""Supported text extraction and context bounds."""

from collections.abc import Mapping, Sequence
from math import isfinite

from .errors import IntegrationError


def argument_text(value: object) -> tuple[str, ...]:
    parts: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise IntegrationError("unsupported_tool_argument")
                parts.append(key)
                visit(child)
        elif isinstance(item, Sequence) and not isinstance(item, (bytes, bytearray, memoryview)):
            for child in item:
                visit(child)
        elif item is None or isinstance(item, (bool, int)) or isinstance(item, float) and isfinite(item):
            return
        else:
            raise IntegrationError("unsupported_tool_argument")

    visit(value)
    return tuple(parts)


def validate_limits(*, text: str = "", messages: int = 0, evidence_items: int = 0) -> None:
    if len(text) > 100_000 or messages > 128 or evidence_items > 64:
        raise IntegrationError("content_limit_exceeded")
    if messages < 0 or evidence_items < 0:
        raise IntegrationError("invalid_content_count")


def extract_snapshot(messages: Sequence[object], *, tool_descriptions: Sequence[str] = (),
                     tool_arguments: Sequence[object] = (), evidence: Sequence[str] = (),
                     answer: str | None = None) -> tuple[str, ...]:
    """Return the ordered text parts at a protected boundary."""
    parts: list[str] = []
    roles = {"system", "developer", "user", "assistant", "tool"}
    for message in messages:
        if not isinstance(message, Mapping) or set(message) != {"role", "content"}:
            raise IntegrationError("unsupported_message")
        if message["role"] not in roles:
            raise IntegrationError("unsupported_role")
        content = message["content"]
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, Sequence) and not isinstance(content, (bytes, bytearray, memoryview)):
            for part in content:
                if not isinstance(part, Mapping) or set(part) != {"type", "text"}:
                    raise IntegrationError("unsupported_content_part")
                if part["type"] != "text" or not isinstance(part["text"], str):
                    raise IntegrationError("unsupported_content_part")
                parts.append(part["text"])
        else:
            raise IntegrationError("unsupported_message_content")
    for description in tool_descriptions:
        if not isinstance(description, str):
            raise IntegrationError("unsupported_tool_description")
        parts.append(description)
    for argument in tool_arguments:
        parts.extend(argument_text(argument))
    for item in evidence:
        if not isinstance(item, str):
            raise IntegrationError("unsupported_evidence")
        parts.append(item)
    if answer is not None:
        if not isinstance(answer, str):
            raise IntegrationError("unsupported_answer")
        parts.append(answer)
    validate_limits(text="".join(parts), messages=len(messages), evidence_items=len(evidence))
    return tuple(parts)
