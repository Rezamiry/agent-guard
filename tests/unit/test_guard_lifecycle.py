from agent_guard import Boundary, CheckKind, CheckPolicy, Guard, PolicySet
from agent_guard.core.errors import ConfigurationError
from agent_guard.core.models import EvaluationContext


class Detector:
    def __init__(self) -> None:
        self.prepared = False

    def prepare(self) -> None:
        self.prepared = True


def test_default_policy_needs_local_detector_before_execution() -> None:
    try:
        Guard().prepare()
    except ConfigurationError as exc:
        assert str(exc) == "local_pii_unavailable"
    else:
        raise AssertionError("required local PII did not block preparation")


def test_default_preparation_uses_local_detector_without_provider() -> None:
    detector = Detector()
    guard = Guard(detector=detector).prepare()
    assert detector.prepared
    guard.close()


def test_enabled_semantic_check_needs_evaluator_but_disabled_does_not() -> None:
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))
    try:
        Guard(policy, detector=Detector()).prepare()
    except ConfigurationError as exc:
        assert str(exc) == "evaluator_unavailable"
    else:
        raise AssertionError("enabled semantic check did not require evaluator")


def test_disabled_checks_do_not_require_or_prepare_dependencies() -> None:
    class Probe:
        def prepare(self) -> None:
            raise AssertionError("disabled dependency was prepared")

    disabled = PolicySet(checks=(
        CheckPolicy("pii_input", CheckKind.PII, Boundary.INPUT, enabled=False),
        CheckPolicy("pii_output", CheckKind.PII, Boundary.OUTPUT, enabled=False),
    ))
    guard = Guard(disabled, detector=Probe()).prepare()
    assert guard.evaluate_input(EvaluationContext("disabled-1", "hello")).allowed
    guard.close()

    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT, enabled=False),
    ))
    class SafeDetector:
        def detect(self, text: str) -> bool:
            return False

    guard = Guard(policy, detector=SafeDetector(), evaluator=Probe()).prepare()
    assert guard.evaluate_output(EvaluationContext("disabled-2", "hello",
                                                   candidate_answer="safe")).allowed
    guard.close()


async def test_async_preparation_validates_local_detector() -> None:
    detector = Detector()
    guard = await Guard(detector=detector).aprepare()
    assert detector.prepared
    await guard.aclose()
    assert guard._closed


def test_closed_guard_cannot_be_prepared_again() -> None:
    guard = Guard(detector=Detector()).prepare()
    guard.close()
    try:
        guard.prepare()
    except ConfigurationError as exc:
        assert str(exc) == "guard_closed"
    else:
        raise AssertionError("closed guard was reused")


async def test_async_core_input_matches_ordinary_decision() -> None:
    class SafeDetector(Detector):
        def detect(self, text: str) -> bool:
            return False

    guard = await Guard(detector=SafeDetector()).aprepare()
    context = EvaluationContext("request-1", "hello")
    assert await guard.aevaluate_input(context) == guard.evaluate_input(context)
    assert (await guard.aenforce_input(context)).allowed
    await guard.aclose()


async def test_async_semantic_evaluator_uses_native_async_path() -> None:
    from agent_guard import CheckResult, Outcome

    class AsyncEvaluator:
        def __init__(self) -> None:
            self.prepared = False
            self.closed = False
            self.calls = 0

        async def aprepare(self) -> None:
            self.prepared = True

        async def aevaluate(self, check: CheckPolicy, context: EvaluationContext) -> CheckResult:
            self.calls += 1
            return CheckResult(check.id, check.boundary, Outcome.PASS,
                               confidence=0.9, evaluator="async-controlled")

        async def aclose(self) -> None:
            self.closed = True

    evaluator = AsyncEvaluator()
    policy = PolicySet(checks=PolicySet().checks + (
        CheckPolicy("relevance", CheckKind.RELEVANCE, Boundary.OUTPUT),
    ))

    class SafeDetector(Detector):
        def detect(self, text: str) -> bool:
            return False

    guard = await Guard(policy, detector=SafeDetector(), evaluator=evaluator).aprepare()
    assert evaluator.prepared
    context = EvaluationContext("async-1", "What?", candidate_answer="A safe answer.")
    assert (await guard.aevaluate_output(context)).allowed
    assert evaluator.calls == 1
    await guard.aclose()
    assert evaluator.closed


def test_setup_failure_is_sanitized() -> None:
    class BrokenDetector(Detector):
        def prepare(self) -> None:
            raise RuntimeError("credential=top-secret")

    try:
        Guard(detector=BrokenDetector()).prepare()
    except ConfigurationError as exc:
        assert "top-secret" not in str(exc)
    else:
        raise AssertionError("detector setup error was not converted")
