"""Microsoft Agent Framework native async middleware."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, cast
from uuid import uuid4

from agent_framework import (
    Agent,
    AgentContext,
    AgentMiddleware,
    AgentResponse,
    ChatContext,
    ChatMiddleware,
    ChatMiddlewareLayer,
    Content,
    ContextProvider,
    Message,
    SessionContext,
)

from agent_guard.core.content import extract_snapshot
from agent_guard.core.errors import ConfigurationError, IntegrationError
from agent_guard.core.guard import Guard
from agent_guard.core.models import EvaluationContext, EvidenceItem
from agent_guard.integrations.common import extract_context, require_prepared_guard

_ROLES = {"system", "developer", "user", "assistant", "tool"}


def _native_message(message: object) -> tuple[dict[str, object], tuple[object, ...]]:
    if not isinstance(message, Message) or message.role not in _ROLES:
        raise IntegrationError("unsupported_native_message")
    parts: list[dict[str, str]] = []
    arguments: list[object] = []
    for content in message.contents:
        if not isinstance(content, Content):
            raise IntegrationError("unsupported_native_content")
        if content.type == "text" and isinstance(content.text, str):
            parts.append({"type": "text", "text": content.text})
        elif content.type == "function_call":
            if content.name is not None:
                arguments.append(content.name)
            if content.arguments is not None:
                arguments.append(content.arguments)
        elif content.type == "function_result" and content.result is not None:
            arguments.append(content.result)
        else:
            raise IntegrationError("unsupported_native_content")
    if message.author_name is not None:
        arguments.append(message.author_name)
    return {"role": message.role, "content": parts}, tuple(arguments)


def _context(messages: object, *, answer: str | None = None,
             evidence: tuple[EvidenceItem, ...] = (),
             generation_id: str | None = None,
             extra_arguments: tuple[object, ...] = ()) -> EvaluationContext:
    if not isinstance(messages, (list, tuple)):
        raise IntegrationError("unsupported_native_messages")
    normalized: list[dict[str, object]] = []
    arguments = list(extra_arguments)
    current_request: str | None = None
    for message in messages:
        item, message_arguments = _native_message(message)
        normalized.append(item)
        arguments.extend(message_arguments)
        if item["role"] == "user":
            current_request = "".join(extract_snapshot((item,)))
    if current_request is None:
        raise IntegrationError("current_request_unavailable")
    return EvaluationContext(uuid4().hex, current_request, tuple(normalized), answer,
                             evidence, generation_id, (), tuple(arguments), True)


def _chat_input_context(context: ChatContext) -> EvaluationContext:
    options = context.options or {}
    tools = options.get("tools") if hasattr(options, "get") else None
    extra_arguments = (tools,) if tools is not None else ()
    return _context(context.messages, extra_arguments=extra_arguments)


def _agent_output_context(context: AgentContext) -> EvaluationContext:
    if not isinstance(context.result, AgentResponse) or not context.result.messages:
        raise IntegrationError("final_answer_unavailable")
    final = context.result.messages[-1]
    if any(content.type != "text" for content in final.contents):
        raise IntegrationError("final_answer_unavailable")
    item, arguments = _native_message(final)
    if item["role"] != "assistant":
        raise IntegrationError("final_answer_unavailable")
    answer = "".join(extract_snapshot((item,)))
    metadata = context.metadata or {}
    evidence = metadata.get("agent_guard_evidence", ()) if hasattr(metadata, "get") else ()
    generation_id = metadata.get("agent_guard_generation_id") if hasattr(metadata, "get") else None
    if not isinstance(evidence, tuple) or any(not isinstance(x, EvidenceItem) for x in evidence):
        raise IntegrationError("unsupported_evidence")
    if generation_id is not None and not isinstance(generation_id, str):
        raise IntegrationError("unsupported_generation_id")
    return _context(context.messages, answer=answer, evidence=evidence,
                    generation_id=generation_id, extra_arguments=arguments)


class MicrosoftChatGuard(ChatMiddleware):
    def __init__(self, guard: Guard) -> None:
        self.guard = guard

    async def process(self, context: ChatContext, call_next: Callable[[], Awaitable[None]]) -> None:
        if context.stream:
            raise ConfigurationError("streaming_unsupported")
        await self.guard.aenforce_input(extract_context(lambda: _chat_input_context(context)))
        await call_next()


class MicrosoftAgentGuard(AgentMiddleware):
    def __init__(self, guard: Guard) -> None:
        self.guard = guard

    async def process(self, context: AgentContext, call_next: Callable[[], Awaitable[None]]) -> None:
        if context.stream:
            raise ConfigurationError("streaming_unsupported")
        await call_next()
        await self.guard.aenforce_output(extract_context(lambda: _agent_output_context(context)))


class _CheckedContextProvider(ContextProvider):
    def __init__(self, provider: ContextProvider) -> None:
        super().__init__(provider.source_id)
        self.provider = provider
        self.after_run_once_per_turn = provider.after_run_once_per_turn

    async def before_run(self, *, agent: Any, session: Any, context: SessionContext,
                         state: dict[str, Any]) -> None:
        prior = {key: tuple(value) for key, value in context.middleware.items()}
        await self.provider.before_run(agent=agent, session=session, context=context, state=state)
        current = {key: tuple(value) for key, value in context.middleware.items()}
        if current != prior:
            raise ConfigurationError("later_provider_middleware_unsupported")

    async def after_run(self, *, agent: Any, session: Any, context: SessionContext,
                        state: dict[str, Any]) -> None:
        await self.provider.after_run(agent=agent, session=session, context=context, state=state)


class GuardedMicrosoftAgent:
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def run(self, messages: Any = None, *, stream: bool = False, **kwargs: Any) -> Awaitable[AgentResponse]:
        if stream:
            raise ConfigurationError("streaming_unsupported")
        return cast(Awaitable[AgentResponse], self._agent.run(messages, stream=False, **kwargs))


def create_guarded_agent(client: Any, guard: Guard, *,
                         context_providers: Sequence[ContextProvider] = ()) -> GuardedMicrosoftAgent:
    require_prepared_guard(guard)
    if not isinstance(client, ChatMiddlewareLayer) or any(
        not isinstance(provider, ContextProvider) for provider in context_providers
    ):
        raise ConfigurationError("unsupported_microsoft_pipeline")
    providers = [_CheckedContextProvider(provider) for provider in context_providers]
    agent = Agent(client=cast(Any, client), context_providers=providers,
                  middleware=[MicrosoftAgentGuard(guard), MicrosoftChatGuard(guard)])
    return GuardedMicrosoftAgent(agent)
