import asyncio

import pytest
from langgraph.graph import END, START, StateGraph

from agent_guard import Guard
from agent_guard.core.errors import ConfigurationError, PolicyViolationError
from agent_guard.core.models import EvaluationContext, EvidenceItem
from agent_guard.integrations.langgraph import (
    AsyncGuardedFinalNode,
    AsyncGuardedModelNode,
    GuardedFinalNode,
    GuardedModelNode,
    compile_guarded_graph,
)


class Detector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


def make_graph(guard: Guard, *, answer: str = "safe", bypass: bool = False):
    calls = {"model": 0}

    def assemble(state):
        evidence = (EvidenceItem("source", state["retrieved_text"], "generation"),) if (
            state.get("retrieved_text")
        ) else ()
        return EvaluationContext("graph-1", state["request"], evidence=evidence)

    def submit(state, context):
        calls["model"] += 1
        return {**state, "answer": answer}

    def final_context(state):
        return EvaluationContext("graph-1", state["request"], candidate_answer=state["answer"])

    builder = StateGraph(dict)
    builder.add_node("retrieve", lambda state: {**state, "retrieved": True})
    builder.add_node("model", GuardedModelNode(guard, assemble, submit))
    builder.add_node("final", GuardedFinalNode(guard, final_context))
    builder.add_conditional_edges(START, lambda state: "retrieve" if state["mode"] == "retrieve" else "model",
                                  {"retrieve": "retrieve", "model": "model"})
    builder.add_edge("retrieve", "model")
    builder.add_edge("model", "final")
    builder.add_edge("final", END)
    if bypass:
        builder.add_edge("model", END)
    return compile_guarded_graph(builder, model_nodes={"model"}, final_nodes={"final"}), calls


def test_real_graph_direct_retrieval_blocks_and_streams() -> None:
    guard = Guard(detector=Detector()).prepare()
    graph, calls = make_graph(guard)
    assert graph.invoke({"request": "hello", "mode": "direct"})["answer"] == "safe"
    assert graph.invoke({"request": "hello", "mode": "retrieve"})["retrieved"] is True
    assert calls["model"] == 2
    with pytest.raises(PolicyViolationError):
        graph.invoke({"request": "secret@example.com", "mode": "direct"})
    assert calls["model"] == 2
    with pytest.raises(ConfigurationError):
        graph.stream({"request": "hello", "mode": "direct"})
    output_graph, _ = make_graph(guard, answer="secret@example.com")
    with pytest.raises(PolicyViolationError):
        output_graph.invoke({"request": "hello", "mode": "direct"})


def test_allowed_result_preserves_caller_defined_state_fields() -> None:
    guard = Guard(detector=Detector()).prepare()
    graph, _ = make_graph(guard)
    result = graph.invoke({
        "request": "hello", "mode": "direct",
        "caller_metadata": {"trace_id": "abc-123", "tenant": "acme"},
    })
    assert result["answer"] == "safe"
    assert result["caller_metadata"] == {"trace_id": "abc-123", "tenant": "acme"}


def test_final_bypass_is_rejected_at_setup() -> None:
    guard = Guard(detector=Detector()).prepare()
    with pytest.raises(ConfigurationError):
        make_graph(guard, bypass=True)


def test_retrieved_pii_blocks_before_real_graph_model_node() -> None:
    guard = Guard(detector=Detector()).prepare()
    graph, calls = make_graph(guard)
    with pytest.raises(PolicyViolationError):
        graph.invoke({"request": "hello", "mode": "retrieve",
                      "retrieved_text": "secret@example.com"})
    assert calls["model"] == 0


async def test_real_graph_ainvoke_matches_ordinary_guarded_boundary() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    graph, calls = make_graph(guard)
    safe = await graph.ainvoke({"request": "hello", "mode": "direct"})
    assert safe["answer"] == "safe"
    assert calls["model"] == 1
    with pytest.raises(PolicyViolationError):
        await graph.ainvoke({"request": "secret@example.com", "mode": "direct"})
    assert calls["model"] == 1
    await guard.aclose()


def test_async_callback_on_sync_node_is_rejected_at_construction() -> None:
    guard = Guard(detector=Detector()).prepare()

    async def async_assemble(state):
        return EvaluationContext("graph-1", state["request"])

    def sync_submit(state, context):
        return state

    with pytest.raises(ConfigurationError) as error:
        GuardedModelNode(guard, async_assemble, sync_submit)
    assert error.value.reason_code == "async_callable_unsupported"

    async def async_submit(state, context):
        return state

    with pytest.raises(ConfigurationError) as error:
        GuardedModelNode(guard, lambda state: EvaluationContext("graph-1", state["request"]),
                         async_submit)
    assert error.value.reason_code == "async_callable_unsupported"

    async def async_final_context(state):
        return EvaluationContext("graph-1", state["request"], candidate_answer=state["answer"])

    with pytest.raises(ConfigurationError) as error:
        GuardedFinalNode(guard, async_final_context)
    assert error.value.reason_code == "async_callable_unsupported"


def make_async_graph(guard: Guard, *, answer: str = "safe"):
    calls = {"model": 0}

    async def assemble(state):
        return EvaluationContext("graph-1", state["request"])

    async def submit(state, context):
        calls["model"] += 1
        return {**state, "answer": answer}

    async def final_context(state):
        return EvaluationContext("graph-1", state["request"], candidate_answer=state["answer"])

    builder = StateGraph(dict)
    builder.add_node("model", AsyncGuardedModelNode(guard, assemble, submit))
    builder.add_node("final", AsyncGuardedFinalNode(guard, final_context))
    builder.add_edge(START, "model")
    builder.add_edge("model", "final")
    builder.add_edge("final", END)
    return compile_guarded_graph(builder, model_nodes={"model"}, final_nodes={"final"}), calls


async def test_async_node_runs_natively_without_executor_thread() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    graph, calls = make_async_graph(guard)
    result = await graph.ainvoke({"request": "hello"})
    assert result["answer"] == "safe"
    assert calls["model"] == 1
    with pytest.raises(PolicyViolationError):
        await graph.ainvoke({"request": "secret@example.com"})
    assert calls["model"] == 1
    await guard.aclose()


async def test_concurrent_async_graph_invocations_do_not_mix_requests() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    graph, calls = make_async_graph(guard)

    async def run(request: str) -> bool:
        try:
            result = await graph.ainvoke({"request": request})
            return result["answer"] == "safe"
        except PolicyViolationError:
            return False

    requests = [f"safe {i}" for i in range(5)] + ["secret@example.com" for _ in range(5)]
    results = await asyncio.gather(*(run(request) for request in requests))
    assert results == [True] * 5 + [False] * 5
    assert calls["model"] == 5
    await guard.aclose()


async def test_async_node_rejects_pii_before_submit_and_reports_native_loop_identity() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    graph, calls = make_async_graph(guard, answer="secret@example.com")
    with pytest.raises(PolicyViolationError):
        await graph.ainvoke({"request": "hello"})

    async def submit_records_loop(state, context):
        calls["loop"] = asyncio.get_running_loop()
        return {**state, "answer": "safe"}

    async def assemble(state):
        return EvaluationContext("graph-1", state["request"])

    node = AsyncGuardedModelNode(guard, assemble, submit_records_loop)
    outer_loop = asyncio.get_running_loop()
    await node({"request": "hello"})
    assert calls["loop"] is outer_loop
    await guard.aclose()
