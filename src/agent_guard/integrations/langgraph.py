"""Declared LangGraph model and final boundary helpers."""

import asyncio
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any, NoReturn

from langgraph.graph import END, START, StateGraph

from agent_guard.core.errors import ConfigurationError
from agent_guard.core.guard import Guard
from agent_guard.core.models import EvaluationContext
from agent_guard.integrations.common import (
    async_extract_context,
    extract_context,
    require_prepared_guard,
)


def _is_coroutine_callable(fn: Callable[..., Any]) -> bool:
    """Detect a coroutine function, including one bound as an object's `__call__`."""
    return asyncio.iscoroutinefunction(fn) or asyncio.iscoroutinefunction(
        getattr(fn, "__call__", None)  # noqa: B004 - checking __call__'s own async-ness, not callability
    )


def _reject_async_callback(*callbacks: Callable[..., Any]) -> None:
    """A synchronous node calling an async callback would silently return an
    un-awaited coroutine as node state; reject that arrangement at construction
    rather than letting LangGraph's executor-thread wrapper run it (FR-34, AC-34)."""
    if any(_is_coroutine_callable(callback) for callback in callbacks):
        raise ConfigurationError("async_callable_unsupported")


class GuardedModelNode:
    def __init__(self, guard: Guard, assemble: Callable[[dict[str, Any]], EvaluationContext],
                 submit: Callable[[dict[str, Any], EvaluationContext], dict[str, Any]]) -> None:
        _reject_async_callback(assemble, submit)
        self.guard = guard
        self.assemble = assemble
        self.submit = submit

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        context = extract_context(lambda: self.assemble(state))
        self.guard.enforce_input(context)
        return self.submit(state, context)


class GuardedFinalNode:
    def __init__(self, guard: Guard, context: Callable[[dict[str, Any]], EvaluationContext]) -> None:
        _reject_async_callback(context)
        self.guard = guard
        self.context = context

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        context = extract_context(lambda: self.context(state))
        self.guard.enforce_output(context)
        return state


def _require_async_callback(*callbacks: Callable[..., Any]) -> None:
    if any(not _is_coroutine_callable(callback) for callback in callbacks):
        raise ConfigurationError("sync_callable_unsupported")


class AsyncGuardedModelNode:
    """LangGraph's native async-node path: runs on the caller's event loop rather
    than in the executor-thread wrapper a synchronous node receives under `ainvoke`."""

    def __init__(self, guard: Guard,
                 assemble: Callable[[dict[str, Any]], Awaitable[EvaluationContext]],
                 submit: Callable[[dict[str, Any], EvaluationContext],
                                  Awaitable[dict[str, Any]]]) -> None:
        _require_async_callback(assemble, submit)
        self.guard = guard
        self.assemble = assemble
        self.submit = submit

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        async def select() -> EvaluationContext:
            return await self.assemble(state)
        context = await async_extract_context(select)
        await self.guard.aenforce_input(context)
        return await self.submit(state, context)


class AsyncGuardedFinalNode:
    def __init__(self, guard: Guard,
                 context: Callable[[dict[str, Any]], Awaitable[EvaluationContext]]) -> None:
        _require_async_callback(context)
        self.guard = guard
        self.context = context

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        async def select() -> EvaluationContext:
            return await self.context(state)
        context = await async_extract_context(select)
        await self.guard.aenforce_output(context)
        return state


class GuardedGraph:
    def __init__(self, graph: Any) -> None:
        self._graph = graph

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return self._graph.invoke(input, config, **kwargs)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return await self._graph.ainvoke(input, config, **kwargs)

    def stream(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("streaming_unsupported")

    def astream(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("streaming_unsupported")

    def astream_events(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise ConfigurationError("streaming_unsupported")


def compile_guarded_graph(builder: StateGraph[Any], *, model_nodes: set[str],
                          final_nodes: set[str]) -> GuardedGraph:
    if not model_nodes or not final_nodes or not model_nodes.isdisjoint(final_nodes):
        raise ConfigurationError("invalid_guarded_topology")
    for name in model_nodes | final_nodes:
        if name not in builder.nodes:
            raise ConfigurationError("missing_guarded_node")
        node = builder.nodes[name].runnable
        sync_instance = getattr(node, "func", None)
        async_instance = getattr(node, "afunc", None)
        expected_sync = GuardedModelNode if name in model_nodes else GuardedFinalNode
        expected_async = AsyncGuardedModelNode if name in model_nodes else AsyncGuardedFinalNode
        if isinstance(sync_instance, expected_sync):
            instance: GuardedModelNode | GuardedFinalNode | AsyncGuardedModelNode | AsyncGuardedFinalNode = sync_instance
        elif sync_instance is None and isinstance(async_instance, expected_async):
            instance = async_instance
        else:
            raise ConfigurationError("invalid_guarded_node")
        require_prepared_guard(instance.guard)
    if builder.waiting_edges:
        raise ConfigurationError("unsupported_join_topology")
    adjacency: dict[str, set[str]] = defaultdict(set)
    for source, target in builder.edges:
        adjacency[source].add(target)
    for source, branches in builder.branches.items():
        for branch in branches.values():
            if branch.ends is None:
                raise ConfigurationError("undeclared_graph_branch")
            adjacency[source].update(branch.ends.values())
    frontier = deque([(START, False)])
    visited: set[tuple[str, bool]] = set()
    found_end = False
    while frontier:
        name, final_seen = frontier.popleft()
        if (name, final_seen) in visited:
            continue
        visited.add((name, final_seen))
        if name in model_nodes:
            final_seen = False
        if name in final_nodes:
            final_seen = True
        if name == END:
            found_end = True
            if not final_seen:
                raise ConfigurationError("unguarded_final_path")
            continue
        for target in adjacency[name]:
            frontier.append((target, final_seen))
    if not found_end:
        raise ConfigurationError("missing_final_path")
    return GuardedGraph(builder.compile())
