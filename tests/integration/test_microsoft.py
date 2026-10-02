import asyncio

import pytest
from agent_framework import (
    Agent,
    AgentContext,
    AgentResponse,
    ChatContext,
    ChatMiddlewareLayer,
    ChatResponse,
    ContextProvider,
    Message,
)

from agent_guard import Guard
from agent_guard.core.errors import ConfigurationError, PolicyViolationError
from agent_guard.integrations.microsoft import (
    MicrosoftAgentGuard,
    MicrosoftChatGuard,
    create_guarded_agent,
)


class Detector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


async def test_native_chat_middleware_checks_post_provider_messages() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    middleware = MicrosoftChatGuard(guard)
    calls = 0
    response = ChatResponse(messages=[Message("assistant", ["safe"])])

    async def next_call() -> None:
        nonlocal calls
        calls += 1
        context.result = response

    context = ChatContext(client=object(), messages=[Message("user", ["hello"])], options=None)
    await middleware.process(context, next_call)
    assert calls == 1
    assert context.result is response
    context = ChatContext(client=object(), messages=[Message("user", ["hello"]),
                                                     Message("tool", ["secret@example.com"])],
                          options=None)
    with pytest.raises(PolicyViolationError):
        await middleware.process(context, next_call)
    assert calls == 1
    stream_context = ChatContext(client=object(), messages=[Message("user", ["hello"])],
                                 options=None, stream=True)
    with pytest.raises(ConfigurationError):
        await middleware.process(stream_context, next_call)
    assert calls == 1
    await guard.aclose()


async def test_native_agent_middleware_checks_final_result_unchanged() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    middleware = MicrosoftAgentGuard(guard)
    safe = AgentResponse(messages=[Message("assistant", ["safe"])])
    context = AgentContext(agent=object(), messages=[Message("user", ["hello"])])

    async def next_safe() -> None:
        context.result = safe

    await middleware.process(context, next_safe)
    assert context.result is safe
    blocked = AgentResponse(messages=[Message("assistant", ["secret@example.com"])])

    async def next_blocked() -> None:
        context.result = blocked

    with pytest.raises(PolicyViolationError):
        await middleware.process(context, next_blocked)
    await guard.aclose()


async def test_real_agent_uses_chat_and_final_middleware() -> None:
    class RawClient:
        async def get_response(self, messages, **kwargs):
            self.calls += 1
            return ChatResponse(messages=[Message("assistant", ["safe"])])

    class FakeClient(ChatMiddlewareLayer, RawClient):
        def __init__(self) -> None:
            self.calls = 0
            super().__init__()

    guard = await Guard(detector=Detector()).aprepare()
    client = FakeClient()
    agent = Agent(client=client, middleware=[MicrosoftAgentGuard(guard), MicrosoftChatGuard(guard)])
    result = await agent.run([Message("user", ["hello"])])
    assert result.text == "safe"
    assert client.calls == 1
    with pytest.raises(PolicyViolationError):
        await agent.run([Message("user", ["secret@example.com"])])
    assert client.calls == 1
    await guard.aclose()


async def test_real_context_provider_addition_is_checked_before_client_call() -> None:
    class RetrievalProvider(ContextProvider):
        async def before_run(self, *, agent, session, context, state) -> None:
            context.extend_messages(self, [Message("tool", ["secret@example.com"])])

    class RawClient:
        async def get_response(self, messages, **kwargs):
            self.calls += 1
            return ChatResponse(messages=[Message("assistant", ["safe"])])

    class FakeClient(ChatMiddlewareLayer, RawClient):
        def __init__(self) -> None:
            self.calls = 0
            super().__init__()

    guard = await Guard(detector=Detector()).aprepare()
    client = FakeClient()
    agent = Agent(client=client, context_providers=[RetrievalProvider("retrieval")],
                  middleware=[MicrosoftAgentGuard(guard), MicrosoftChatGuard(guard)])
    with pytest.raises(PolicyViolationError):
        await agent.run([Message("user", ["hello"])])
    assert client.calls == 0
    await guard.aclose()


async def test_guarded_facade_rejects_stream_and_late_provider_middleware() -> None:
    class RawClient:
        async def get_response(self, messages, **kwargs):
            self.calls += 1
            return ChatResponse(messages=[Message("assistant", ["safe"])])

    class FakeClient(ChatMiddlewareLayer, RawClient):
        def __init__(self) -> None:
            self.calls = 0
            super().__init__()

    class LaterProvider(ContextProvider):
        async def before_run(self, *, agent, session, context, state) -> None:
            context.extend_middleware(self, [MicrosoftChatGuard(guard)])

    guard = await Guard(detector=Detector()).aprepare()
    client = FakeClient()
    agent = create_guarded_agent(client, guard, context_providers=(LaterProvider("late"),))
    with pytest.raises(ConfigurationError):
        agent.run([Message("user", ["hello"])], stream=True)
    with pytest.raises(ConfigurationError):
        await agent.run([Message("user", ["hello"])])
    assert client.calls == 0
    await guard.aclose()


async def test_concurrent_agent_runs_do_not_mix_requests() -> None:
    class RawClient:
        async def get_response(self, messages, **kwargs):
            self.calls += 1
            return ChatResponse(messages=[Message("assistant", ["safe"])])

    class FakeClient(ChatMiddlewareLayer, RawClient):
        def __init__(self) -> None:
            self.calls = 0
            super().__init__()

    guard = await Guard(detector=Detector()).aprepare()
    client = FakeClient()
    agent = create_guarded_agent(client, guard)

    async def run(text: str) -> bool:
        try:
            await agent.run([Message("user", [text])])
            return True
        except PolicyViolationError:
            return False

    requests = [f"question {i}" for i in range(5)] + ["secret@example.com" for _ in range(5)]
    results = await asyncio.gather(*(run(text) for text in requests))
    assert results == [True] * 5 + [False] * 5
    assert client.calls == 5
    await guard.aclose()


async def test_guarded_facade_sees_provider_added_message_text() -> None:
    class RetrievalProvider(ContextProvider):
        async def before_run(self, *, agent, session, context, state) -> None:
            context.extend_messages(self, [Message("tool", ["secret@example.com"])])

    class RawClient:
        async def get_response(self, messages, **kwargs):
            self.calls += 1
            return ChatResponse(messages=[Message("assistant", ["safe"])])

    class FakeClient(ChatMiddlewareLayer, RawClient):
        def __init__(self) -> None:
            self.calls = 0
            super().__init__()

    guard = await Guard(detector=Detector()).aprepare()
    client = FakeClient()
    agent = create_guarded_agent(client, guard,
                                 context_providers=(RetrievalProvider("retrieval"),))
    with pytest.raises(PolicyViolationError):
        await agent.run([Message("user", ["hello"])])
    assert client.calls == 0
    await guard.aclose()
