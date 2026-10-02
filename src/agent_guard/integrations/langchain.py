"""Native LangChain agent middleware."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, NoReturn
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from agent_guard.core.content import extract_snapshot
from agent_guard.core.errors import ConfigurationError, IntegrationError
from agent_guard.core.guard import Guard
from agent_guard.core.models import EvaluationContext, EvidenceItem
from agent_guard.integrations.common import extract_context, require_prepared_guard

_ROLES = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}


def _native_message(message: object) -> tuple[dict[str, object], tuple[object, ...], tuple[str, ...]]:
    if not isinstance(message, BaseMessage) or message.type not in _ROLES:
        raise IntegrationError("unsupported_native_message")
    content = message.content
    if isinstance(content, str):
        normalized: str | list[dict[str, str]] = content
    elif isinstance(content, list):
        normalized = []
        for part in content:
            if isinstance(part, str):
                normalized.append({"type": "text", "text": part})
            elif isinstance(part, Mapping) and set(part) == {"type", "text"} and (
                part.get("type") == "text" and isinstance(part.get("text"), str)
            ):
                normalized.append({"type": "text", "text": part["text"]})
            else:
                raise IntegrationError("unsupported_native_content")
    else:
        raise IntegrationError("unsupported_native_content")
    arguments: list[object] = []
    if isinstance(message, AIMessage):
        if message.invalid_tool_calls:
            raise IntegrationError("unsupported_tool_call")
        arguments.extend(message.tool_calls)
    if message.additional_kwargs:
        arguments.append(message.additional_kwargs)
    names = (message.name,) if isinstance(message.name, str) else ()
    return {"role": _ROLES[message.type], "content": normalized}, tuple(arguments), names


def _native_context(messages: Sequence[object], *, answer: str | None = None,
                    tools: Sequence[object] = (), tool_choice: object = None,
                    model_settings: Mapping[str, object] | None = None,
                    evidence: tuple[EvidenceItem, ...] = (),
                    generation_id: str | None = None) -> EvaluationContext:
    normalized: list[dict[str, object]] = []
    arguments: list[object] = []
    descriptions: list[str] = []
    current_request: str | None = None
    for message in messages:
        item, message_arguments, names = _native_message(message)
        normalized.append(item)
        arguments.extend(message_arguments)
        descriptions.extend(names)
        if item["role"] == "user":
            current_request = "".join(extract_snapshot((item,)))
    if current_request is None:
        raise IntegrationError("current_request_unavailable")
    for tool in tools:
        if isinstance(tool, BaseTool):
            arguments.append(convert_to_openai_tool(tool))
        elif isinstance(tool, Mapping):
            arguments.append(tool)
        else:
            raise IntegrationError("unsupported_tool_definition")
    if tool_choice is not None:
        arguments.append(tool_choice)
    if model_settings:
        arguments.append(model_settings)
    return EvaluationContext(
        uuid4().hex, current_request, tuple(normalized), answer, evidence, generation_id,
        tuple(descriptions), tuple(arguments), True,
    )


class InputGuardMiddleware(AgentMiddleware):
    def __init__(self, guard: Guard) -> None:
        super().__init__()
        self.guard = guard

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        messages: list[object] = []
        if request.system_message is not None:
            messages.append(request.system_message)
        messages.extend(request.messages)
        if request.response_format is not None:
            raise IntegrationError("unsupported_response_format")
        context = extract_context(lambda: _native_context(
            messages, tools=request.tools, tool_choice=request.tool_choice,
            model_settings=request.model_settings,
        ))
        self.guard.enforce_input(context)
        return handler(request)

    async def awrap_model_call(self, request: ModelRequest,
                               handler: Callable[[ModelRequest], Awaitable[ModelResponse]]) -> ModelResponse:
        messages: list[object] = []
        if request.system_message is not None:
            messages.append(request.system_message)
        messages.extend(request.messages)
        if request.response_format is not None:
            raise IntegrationError("unsupported_response_format")
        context = extract_context(lambda: _native_context(
            messages, tools=request.tools, tool_choice=request.tool_choice,
            model_settings=request.model_settings,
        ))
        await self.guard.aenforce_input(context)
        return await handler(request)


class OutputGuardMiddleware(AgentMiddleware):
    def __init__(self, guard: Guard) -> None:
        super().__init__()
        self.guard = guard

    def _context(self, state: object) -> EvaluationContext:
        if not isinstance(state, Mapping):
            raise IntegrationError("unsupported_agent_state")
        messages = state.get("messages")
        if not isinstance(messages, (list, tuple)) or not messages:
            raise IntegrationError("final_answer_unavailable")
        final = messages[-1]
        if not isinstance(final, AIMessage) or final.tool_calls or final.invalid_tool_calls:
            raise IntegrationError("final_answer_unavailable")
        item, arguments, _ = _native_message(final)
        if arguments:
            raise IntegrationError("unsupported_final_metadata")
        answer = "".join(extract_snapshot((item,)))
        evidence = state.get("agent_guard_evidence", ())
        generation_id = state.get("agent_guard_generation_id")
        if not isinstance(evidence, tuple) or any(not isinstance(x, EvidenceItem) for x in evidence):
            raise IntegrationError("unsupported_evidence")
        if generation_id is not None and not isinstance(generation_id, str):
            raise IntegrationError("unsupported_generation_id")
        return _native_context(messages[:-1], answer=answer, evidence=evidence,
                               generation_id=generation_id)

    def after_agent(self, state: Any, runtime: Any) -> None:
        self.guard.enforce_output(extract_context(lambda: self._context(state)))

    async def aafter_agent(self, state: Any, runtime: Any) -> None:
        await self.guard.aenforce_output(extract_context(lambda: self._context(state)))


class GuardedLangChainAgent:
    """Expose only the guarded ordinary and async non-streaming paths."""

    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return self._agent.invoke(input, config, **kwargs)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return await self._agent.ainvoke(input, config, **kwargs)

    def stream(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("streaming_unsupported")

    def astream(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("streaming_unsupported")

    def astream_events(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("streaming_unsupported")

    def batch(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("batch_unsupported")

    def abatch(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("batch_unsupported")


def create_guarded_agent(model: str | BaseChatModel, *,
                         tools: Sequence[BaseTool | Callable[..., Any] | dict[str, Any]],
                         guard: Guard, middleware: Sequence[AgentMiddleware] = ()) -> GuardedLangChainAgent:
    require_prepared_guard(guard)
    agent = create_agent(
        model=model, tools=tools,
        middleware=[OutputGuardMiddleware(guard), *middleware, InputGuardMiddleware(guard)],
    )
    return GuardedLangChainAgent(agent)
