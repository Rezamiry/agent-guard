"""Identical controlled judgments must produce identical decisions across every
supported execution surface and offline evaluation (AC-12, FR-20, SC-003)."""

from agent_framework import Agent, ChatMiddlewareLayer, ChatResponse, Message
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph import END, START, StateGraph

from agent_guard import Guard
from agent_guard.core.errors import PolicyViolationError
from agent_guard.core.models import EvaluationContext
from agent_guard.evaluation.dataset import SavedExample
from agent_guard.evaluation.runner import run_saved
from agent_guard.integrations.langchain import create_guarded_agent as create_langchain_agent
from agent_guard.integrations.langgraph import (
    GuardedFinalNode,
    GuardedModelNode,
    compile_guarded_graph,
)
from agent_guard.integrations.microsoft import MicrosoftAgentGuard


class Detector:
    def detect(self, text: str) -> bool:
        return "secret@example.com" in text


def _core_allowed(guard: Guard, answer: str) -> bool:
    return guard.evaluate_output(
        EvaluationContext("core", "question", candidate_answer=answer)
    ).allowed


def _langchain_allowed(guard: Guard, answer: str) -> bool:
    agent = create_langchain_agent(FakeListChatModel(responses=[answer]), tools=[], guard=guard)
    try:
        agent.invoke({"messages": [{"role": "user", "content": "question"}]})
        return True
    except PolicyViolationError:
        return False


def _langgraph_allowed(guard: Guard, answer: str) -> bool:
    def assemble(state: dict) -> EvaluationContext:
        return EvaluationContext("graph", "question")

    def submit(state: dict, context: EvaluationContext) -> dict:
        return {**state, "answer": answer}

    def final_context(state: dict) -> EvaluationContext:
        return EvaluationContext("graph", "question", candidate_answer=state["answer"])

    builder = StateGraph(dict)
    builder.add_node("model", GuardedModelNode(guard, assemble, submit))
    builder.add_node("final", GuardedFinalNode(guard, final_context))
    builder.add_edge(START, "model")
    builder.add_edge("model", "final")
    builder.add_edge("final", END)
    graph = compile_guarded_graph(builder, model_nodes={"model"}, final_nodes={"final"})
    try:
        graph.invoke({"question": "question"})
        return True
    except PolicyViolationError:
        return False


async def _microsoft_allowed(guard: Guard, answer: str) -> bool:
    class RawClient:
        async def get_response(self, messages: object, **kwargs: object) -> ChatResponse:
            return ChatResponse(messages=[Message("assistant", [answer])])

    class FakeClient(ChatMiddlewareLayer, RawClient):
        def __init__(self) -> None:
            super().__init__()

    agent = Agent(client=FakeClient(), middleware=[MicrosoftAgentGuard(guard)])
    try:
        await agent.run([Message("user", ["question"])])
        return True
    except PolicyViolationError:
        return False


def _offline_allowed(guard: Guard, answer: str) -> bool:
    example = SavedExample("offline", EvaluationContext("offline", "question",
                                                        candidate_answer=answer))
    result = run_saved(guard, (example,))[0]
    assert result.output_decision is not None
    return result.output_decision.allowed


async def test_safe_answer_is_delivered_unchanged_on_every_surface() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    answer = "Everything looks good."
    assert _core_allowed(guard, answer) is True
    assert _langchain_allowed(guard, answer) is True
    assert _langgraph_allowed(guard, answer) is True
    assert await _microsoft_allowed(guard, answer) is True
    assert _offline_allowed(guard, answer) is True
    await guard.aclose()


async def test_pii_bearing_answer_is_blocked_identically_on_every_surface() -> None:
    guard = await Guard(detector=Detector()).aprepare()
    answer = "Contact secret@example.com for details."
    assert _core_allowed(guard, answer) is False
    assert _langchain_allowed(guard, answer) is False
    assert _langgraph_allowed(guard, answer) is False
    assert await _microsoft_allowed(guard, answer) is False
    assert _offline_allowed(guard, answer) is False
    await guard.aclose()
