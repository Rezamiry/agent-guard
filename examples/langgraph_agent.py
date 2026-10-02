"""Declared native LangGraph direct and retrieval paths."""

from langgraph.graph import END, START, StateGraph

from agent_guard import Guard
from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.core.errors import PolicyViolationError
from agent_guard.core.models import EvaluationContext
from agent_guard.integrations.langgraph import (
    GuardedFinalNode,
    GuardedModelNode,
    compile_guarded_graph,
)


def main() -> None:
    guard = Guard(detector=LocalPIIDetector()).prepare()
    try:
        builder = StateGraph(dict)
        builder.add_node("retrieve", lambda state: {**state, "retrieved": True})
        builder.add_node("model", GuardedModelNode(
            guard, lambda state: EvaluationContext("graph-example", state["request"]),
            lambda state, _: {**state, "answer": "safe"},
        ))
        builder.add_node("final", GuardedFinalNode(
            guard, lambda state: EvaluationContext("graph-example", state["request"],
                                                   candidate_answer=state["answer"]),
        ))
        builder.add_conditional_edges(START, lambda state: state["route"],
                                      {"direct": "model", "retrieve": "retrieve"})
        builder.add_edge("retrieve", "model")
        builder.add_edge("model", "final")
        builder.add_edge("final", END)
        graph = compile_guarded_graph(builder, model_nodes={"model"}, final_nodes={"final"})
        print("direct:", graph.invoke({"request": "hello", "route": "direct"})["answer"])
        print("retrieval:", graph.invoke({"request": "hello", "route": "retrieve"})["retrieved"])
        try:
            graph.invoke({"request": "secret@example.com", "route": "retrieve"})
        except PolicyViolationError as exc:
            print("blocked retrieved path:", exc.reason_code)
    finally:
        guard.close()


if __name__ == "__main__":
    main()
