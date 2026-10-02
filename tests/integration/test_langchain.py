import asyncio
from collections.abc import Callable

import pytest
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from pydantic import Field

from agent_guard import Guard
from agent_guard.core.errors import ConfigurationError, PolicyViolationError
from agent_guard.integrations.langchain import (
    InputGuardMiddleware,
    OutputGuardMiddleware,
    create_guarded_agent,
)


class Detector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


def test_native_model_wrapper_preserves_response_and_blocks_tool_argument_pii() -> None:
    guard = Guard(detector=Detector()).prepare()
    middleware = InputGuardMiddleware(guard)
    model = FakeListChatModel(responses=["safe"])
    response = ModelResponse([AIMessage("safe")])
    calls = 0

    def handler(request: ModelRequest) -> ModelResponse:
        nonlocal calls
        calls += 1
        return response

    safe = ModelRequest(model=model, messages=[HumanMessage("hello")])
    assert middleware.wrap_model_call(safe, handler) is response
    assert calls == 1
    blocked = ModelRequest(model=model, messages=[HumanMessage("hello")],
                           tools=[{"name": "lookup", "description": "Search",
                                   "parameters": {"secret@example.com": "string"}}])
    with pytest.raises(PolicyViolationError):
        middleware.wrap_model_call(blocked, handler)
    assert calls == 1


def test_native_final_hook_checks_completed_answer() -> None:
    guard = Guard(detector=Detector()).prepare()
    middleware = OutputGuardMiddleware(guard)
    safe = {"messages": [HumanMessage("hello"), AIMessage("safe") ]}
    assert middleware.after_agent(safe, None) is None
    blocked = {"messages": [HumanMessage("hello"), AIMessage("secret@example.com") ]}
    with pytest.raises(PolicyViolationError):
        middleware.after_agent(blocked, None)


def test_real_agent_safe_blocked_and_stream_rejection() -> None:
    guard = Guard(detector=Detector()).prepare()
    safe_model = FakeListChatModel(responses=["safe"])
    agent = create_guarded_agent(safe_model, tools=[], guard=guard)
    result = agent.invoke({"messages": [{"role": "user", "content": "hello"}]})
    assert result["messages"][-1].content == "safe"
    with pytest.raises(ConfigurationError):
        agent.stream({"messages": [{"role": "user", "content": "hello"}]})
    with pytest.raises(PolicyViolationError):
        agent.invoke({"messages": [{"role": "user", "content": "secret@example.com"}]})
    output_model = FakeListChatModel(responses=["secret@example.com"])
    output_agent = create_guarded_agent(output_model, tools=[], guard=guard)
    with pytest.raises(PolicyViolationError):
        output_agent.invoke({"messages": [{"role": "user", "content": "hello"}]})


async def test_native_async_model_and_final_hooks() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    middleware = InputGuardMiddleware(guard)
    response = ModelResponse([AIMessage("safe")])
    calls = 0

    async def handler(request: ModelRequest) -> ModelResponse:
        nonlocal calls
        calls += 1
        return response

    safe = ModelRequest(model=FakeListChatModel(responses=["safe"]),
                        messages=[HumanMessage("hello")])
    assert await middleware.awrap_model_call(safe, handler) is response
    blocked = ModelRequest(model=safe.model, messages=[HumanMessage("secret@example.com")])
    with pytest.raises(PolicyViolationError):
        await middleware.awrap_model_call(blocked, handler)
    assert calls == 1
    output = OutputGuardMiddleware(guard)
    assert await output.aafter_agent({"messages": [HumanMessage("hello"), AIMessage("safe")]}, None) is None
    with pytest.raises(PolicyViolationError):
        await output.aafter_agent({"messages": [HumanMessage("hello"),
                                               AIMessage("secret@example.com")]}, None)
    await guard.aclose()


async def test_concurrent_ainvoke_calls_do_not_mix_requests() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    safe_model = FakeListChatModel(responses=["safe"] * 10)
    agent = create_guarded_agent(safe_model, tools=[], guard=guard)

    async def run(request: str) -> bool:
        try:
            await agent.ainvoke({"messages": [{"role": "user", "content": request}]})
            return True
        except PolicyViolationError:
            return False

    requests = [f"question {i}" for i in range(5)] + ["secret@example.com" for _ in range(5)]
    results = await asyncio.gather(*(run(request) for request in requests))
    assert results == [True] * 5 + [False] * 5
    await guard.aclose()


class _ScriptedToolModel(BaseChatModel):
    """A real `BaseChatModel` that requests one tool call, then returns text."""

    turns: list[AIMessage] = Field(default_factory=list)
    calls: list[int] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-model"

    def bind_tools(self, tools: object, **kwargs: object) -> "BaseChatModel":
        return self

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  run_manager: object = None, **kwargs: object) -> ChatResult:
        index = len(self.calls)
        self.calls.append(index)
        return ChatResult(generations=[ChatGeneration(message=self.turns[index])])


@tool
def lookup(query: str) -> str:
    """Look up account contact details for the given query."""
    return "Contact secret@example.com for account details."


@tool
def safe_lookup(query: str) -> str:
    """Look up the current weather for the given query."""
    return "It is sunny today."


class _LateMutator(AgentMiddleware):
    """A user middleware that adds PII-bearing content before calling the handler."""

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        mutated = request.override(messages=[*request.messages,
                                             HumanMessage("secret@example.com")])
        return handler(mutated)


def test_user_middleware_mutation_before_guard_is_still_checked() -> None:
    # create_guarded_agent places InputGuardMiddleware last (closest to the
    # model), so it always sees what any caller-supplied middleware passed
    # down the chain -- there is no way to register a later mutator that
    # bypasses it through this facade (FR-32, FR-34).
    guard = Guard(detector=Detector()).prepare()
    model = FakeListChatModel(responses=["safe"])
    agent = create_guarded_agent(model, tools=[], guard=guard, middleware=[_LateMutator()])
    with pytest.raises(PolicyViolationError):
        agent.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_allowed_result_preserves_native_metadata_and_id() -> None:
    guard = Guard(detector=Detector()).prepare()
    tagged = AIMessage(
        "Everything looks good.", id="run-42",
        response_metadata={"model_name": "scripted", "finish_reason": "stop"},
        usage_metadata={"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
    )
    model = _ScriptedToolModel(turns=[tagged])
    agent = create_guarded_agent(model, tools=[], guard=guard)
    result = agent.invoke({"messages": [{"role": "user", "content": "How are things?"}]})
    final = result["messages"][-1]
    assert final.content == "Everything looks good."
    assert final.id == "run-42"
    assert final.response_metadata == {"model_name": "scripted", "finish_reason": "stop"}
    assert final.usage_metadata == {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7}


def test_real_tool_calling_loop_completes_when_tool_output_is_safe() -> None:
    guard = Guard(detector=Detector()).prepare()
    model = _ScriptedToolModel(turns=[
        AIMessage("", tool_calls=[{"name": "safe_lookup", "args": {"query": "weather"},
                                   "id": "c1"}]),
        AIMessage("It is sunny today."),
    ])
    agent = create_guarded_agent(model, tools=[safe_lookup], guard=guard)
    result = agent.invoke({"messages": [{"role": "user", "content": "What's the weather?"}]})
    assert result["messages"][-1].content == "It is sunny today."
    # Both the tool-requesting turn and the final-answer turn were each checked
    # once, and the intermediate tool-call message was never treated as final.
    assert model.calls == [0, 1]


def test_real_tool_calling_loop_rechecks_second_model_request_with_tool_output() -> None:
    guard = Guard(detector=Detector()).prepare()
    model = _ScriptedToolModel(turns=[
        AIMessage("", tool_calls=[{"name": "lookup", "args": {"query": "account"}, "id": "c1"}]),
        AIMessage("Here is the info you asked for."),
    ])
    agent = create_guarded_agent(model, tools=[lookup], guard=guard)
    with pytest.raises(PolicyViolationError):
        agent.invoke({"messages": [{"role": "user", "content": "How do I contact support?"}]})
    # The first (tool-requesting) turn was allowed and the tool ran; the second
    # assembled request, now carrying the tool's PII output, was independently
    # rechecked and blocked before that second model call ever happened.
    assert model.calls == [0]


async def test_real_agent_ainvoke_checks_input_and_final_answer() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    safe_model = FakeListChatModel(responses=["safe"])
    agent = create_guarded_agent(safe_model, tools=[], guard=guard)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": "hello"}]})
    assert result["messages"][-1].content == "safe"
    with pytest.raises(PolicyViolationError):
        await agent.ainvoke({"messages": [{"role": "user", "content": "secret@example.com"}]})
    output_model = FakeListChatModel(responses=["secret@example.com"])
    output_agent = create_guarded_agent(output_model, tools=[], guard=guard)
    with pytest.raises(PolicyViolationError):
        await output_agent.ainvoke({"messages": [{"role": "user", "content": "hello"}]})
    await guard.aclose()
