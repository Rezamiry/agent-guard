"""Real native-object content and adapter fault contracts."""

import asyncio
from collections.abc import Iterator, Mapping

import pytest
from agent_framework import AgentContext, ChatContext, Message
from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from agent_guard import Guard
from agent_guard.core.errors import IntegrationError, PolicyViolationError
from agent_guard.integrations.langchain import InputGuardMiddleware, OutputGuardMiddleware
from agent_guard.integrations.microsoft import MicrosoftAgentGuard, MicrosoftChatGuard


class SafeDetector:
    def detect(self, text: str) -> bool:
        return False


class RecordingDetector:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def detect(self, text: str) -> bool:
        self.parts.append(text)
        return "secret@example.com" in text


def test_native_multipart_text_and_nested_tool_arguments_are_inspected() -> None:
    detector = RecordingDetector()
    middleware = InputGuardMiddleware(Guard(detector=detector).prepare())
    model = FakeListChatModel(responses=["safe"])
    calls = 0

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse([AIMessage("safe")])

    request = ModelRequest(model=model, messages=[HumanMessage(content=[
        {"type": "text", "text": "part one"},
        {"type": "text", "text": "part two"},
    ])], tools=[{"name": "lookup", "parameters": {"nested": [
        {"query": "ordinary"},
    ]}}])
    middleware.wrap_model_call(request, handler)
    assert calls == 1
    assert len(detector.parts) == 1
    inspected = detector.parts[0]
    assert inspected.index("part one") < inspected.index("part two")
    assert inspected.index("name\nlookup\nparameters\nnested\nquery\nordinary") > inspected.index(
        "part two"
    )

    blocked = ModelRequest(model=model, messages=[HumanMessage("hello")], tools=[
        {"name": "lookup", "parameters": {"nested": [{"query": "secret@example.com"}]}},
    ])
    with pytest.raises(PolicyViolationError):
        middleware.wrap_model_call(blocked, handler)
    assert calls == 1


def test_exact_native_text_limit_passes_and_overflow_stops_handoff() -> None:
    guard = Guard(detector=SafeDetector()).prepare()
    middleware = InputGuardMiddleware(guard)
    calls = 0
    response = ModelResponse([AIMessage("safe")])

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal calls
        calls += 1
        return response

    model = FakeListChatModel(responses=["safe"])
    exact = ModelRequest(model=model, messages=[HumanMessage("x" * 100_000)])
    assert middleware.wrap_model_call(exact, handler) is response
    assert calls == 1
    overflow = ModelRequest(model=model, messages=[HumanMessage("x" * 100_001)])
    with pytest.raises(IntegrationError):
        middleware.wrap_model_call(overflow, handler)
    assert calls == 1


def test_opaque_native_part_rejects_before_handoff() -> None:
    guard = Guard(detector=SafeDetector()).prepare()
    middleware = InputGuardMiddleware(guard)
    model = FakeListChatModel(responses=["safe"])
    request = ModelRequest(model=model, messages=[HumanMessage(content=[
        {"type": "image_url", "image_url": "data:image/png;base64,AA=="},
    ])])
    calls = 0

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse([AIMessage("safe")])

    with pytest.raises(IntegrationError):
        middleware.wrap_model_call(request, handler)
    assert calls == 0


def test_unexpected_native_state_extraction_fault_is_sanitized() -> None:
    class BrokenState(Mapping[str, object]):
        def __iter__(self) -> Iterator[str]:
            return iter(("messages",))

        def __len__(self) -> int:
            return 1

        def __getitem__(self, key: str) -> object:
            raise RuntimeError("secret@example.com")

        def get(self, key: str, default: object = None) -> object:
            raise RuntimeError("secret@example.com")

    middleware = OutputGuardMiddleware(Guard(detector=SafeDetector()).prepare())
    with pytest.raises(IntegrationError) as error:
        middleware.after_agent(BrokenState(), None)
    assert "secret@example.com" not in str(error.value)


@pytest.mark.parametrize("failure", [RuntimeError("caller failed"), asyncio.CancelledError()])
async def test_langchain_async_model_handler_caller_failure_keeps_identity(
    failure: BaseException,
) -> None:
    middleware = InputGuardMiddleware(Guard(detector=SafeDetector()).prepare())
    request = ModelRequest(model=FakeListChatModel(responses=["safe"]),
                           messages=[HumanMessage("hello")])

    async def handler(_: ModelRequest) -> ModelResponse:
        raise failure

    with pytest.raises(type(failure)) as error:
        await middleware.awrap_model_call(request, handler)
    assert error.value is failure


@pytest.mark.parametrize("failure", [RuntimeError("caller failed"), asyncio.CancelledError()])
async def test_microsoft_chat_middleware_call_next_failure_keeps_identity(
    failure: BaseException,
) -> None:
    guard = await Guard(detector=SafeDetector()).aprepare()
    middleware = MicrosoftChatGuard(guard)
    context = ChatContext(client=object(), messages=[Message("user", ["hello"])], options=None)

    async def call_next() -> None:
        raise failure

    with pytest.raises(type(failure)) as error:
        await middleware.process(context, call_next)
    assert error.value is failure
    await guard.aclose()


@pytest.mark.parametrize("failure", [RuntimeError("caller failed"), asyncio.CancelledError()])
async def test_microsoft_agent_middleware_call_next_failure_keeps_identity(
    failure: BaseException,
) -> None:
    guard = await Guard(detector=SafeDetector()).aprepare()
    middleware = MicrosoftAgentGuard(guard)
    context = AgentContext(agent=object(), messages=[Message("user", ["hello"])])

    async def call_next() -> None:
        raise failure

    with pytest.raises(type(failure)) as error:
        await middleware.process(context, call_next)
    assert error.value is failure
    await guard.aclose()


@pytest.mark.parametrize("failure", [RuntimeError("caller failed"), asyncio.CancelledError()])
async def test_langgraph_async_model_node_submit_failure_keeps_identity(
    failure: BaseException,
) -> None:
    pytest.importorskip("langgraph")
    from agent_guard.core.models import EvaluationContext
    from agent_guard.integrations.langgraph import AsyncGuardedModelNode

    guard = await Guard(detector=SafeDetector()).aprepare()

    async def assemble(state: dict[str, object]) -> "EvaluationContext":
        return EvaluationContext("r1", "hello")

    async def submit(state: dict[str, object], context: "EvaluationContext") -> dict[str, object]:
        raise failure

    node = AsyncGuardedModelNode(guard, assemble, submit)
    with pytest.raises(type(failure)) as error:
        await node({"request": "hello"})
    assert error.value is failure
    await guard.aclose()
