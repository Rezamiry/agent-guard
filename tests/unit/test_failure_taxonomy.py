import asyncio

import pytest

from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, Outcome, PolicySet
from agent_guard.core.errors import ConfigurationError, EvaluationError, IntegrationError
from agent_guard.core.models import EvaluationContext


class SafeDetector:
    def detect(self, text: str) -> bool:
        return False


def test_optional_runtime_provider_failure_is_recorded_with_reason() -> None:
    class TimeoutEvaluator:
        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> Outcome:
            raise EvaluationError("provider_timeout")

    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT, required=False),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=TimeoutEvaluator()).prepare()
    result = guard.evaluate_output(EvaluationContext("r1", "What?", candidate_answer="Safe")).results[-1]
    assert result.outcome == Outcome.EVALUATION_ERROR
    assert result.reason_code == "provider_timeout"


def test_integration_fault_stops_even_optional_policy() -> None:
    class BrokenEvaluator:
        def evaluate(self, check: CheckPolicy, context: EvaluationContext) -> Outcome:
            raise IntegrationError("native_extraction_failed")

    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT, required=False),
    ))
    guard = Guard(policy, detector=SafeDetector(), evaluator=BrokenEvaluator()).prepare()
    with pytest.raises(IntegrationError) as error:
        guard.evaluate_output(EvaluationContext("r2", "What?", candidate_answer="Safe"))
    assert error.value.reason_code == "native_extraction_failed"


def test_native_assembler_fault_is_sanitized_integration_failure() -> None:
    pytest.importorskip("langgraph")
    from agent_guard.integrations.langgraph import GuardedModelNode

    policy = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT, required=False),
    ))
    guard = Guard(policy, detector=SafeDetector()).prepare()
    model_calls = 0

    def assemble(state: dict[str, object]) -> EvaluationContext:
        raise RuntimeError("raw state secret@example.com")

    def submit(state: dict[str, object], context: EvaluationContext) -> dict[str, object]:
        nonlocal model_calls
        model_calls += 1
        return state

    with pytest.raises(IntegrationError) as error:
        GuardedModelNode(guard, assemble, submit)({"request": "safe"})
    assert error.value.reason_code == "native_extraction_failed"
    assert "secret@example.com" not in str(error.value)
    assert model_calls == 0


@pytest.mark.parametrize("failure", [RuntimeError("caller failed"), asyncio.CancelledError()])
def test_native_protected_caller_failure_keeps_identity(failure: BaseException) -> None:
    pytest.importorskip("langgraph")
    from agent_guard.integrations.langgraph import GuardedModelNode

    guard = Guard(detector=SafeDetector()).prepare()

    def assemble(state: dict[str, object]) -> EvaluationContext:
        return EvaluationContext("r3", "safe")

    def submit(state: dict[str, object], context: EvaluationContext) -> dict[str, object]:
        raise failure

    with pytest.raises(type(failure)) as error:
        GuardedModelNode(guard, assemble, submit)({"request": "safe"})
    assert error.value is failure


def test_native_final_selector_fault_is_integration_error() -> None:
    pytest.importorskip("langgraph")
    from agent_guard.integrations.langgraph import GuardedFinalNode

    guard = Guard(detector=SafeDetector()).prepare()

    def select_final(state: dict[str, object]) -> EvaluationContext:
        raise RuntimeError("answer secret@example.com")

    with pytest.raises(IntegrationError) as error:
        GuardedFinalNode(guard, select_final)({"answer": "safe"})
    assert error.value.reason_code == "native_extraction_failed"
    assert "secret@example.com" not in str(error.value)


def test_known_invalid_graph_topology_is_configuration_failure() -> None:
    pytest.importorskip("langgraph")
    from langgraph.graph import StateGraph

    from agent_guard.integrations.langgraph import compile_guarded_graph

    with pytest.raises(ConfigurationError) as error:
        compile_guarded_graph(StateGraph(dict), model_nodes=set(), final_nodes={"final"})
    assert error.value.reason_code == "invalid_guarded_topology"
