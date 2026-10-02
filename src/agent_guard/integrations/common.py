"""Shared native-boundary extraction and failure classification.

This module holds what is actually common across two or more integrations: adapter
extraction-fault classification and the prepared-guard check. Per-framework structural
validation deliberately stays in its own adapter module rather than being generalized here:

- LangGraph's `compile_guarded_graph` performs graph-topology validation (edge reachability,
  a bypass path to END, waiting-edge rejection). `StateGraph` edges have no equivalent in
  LangChain's middleware pipeline or Microsoft's `ChatMiddlewareLayer`/`ContextProvider`
  model, so there is no second consumer to justify lifting this into a shared abstraction
  (see the constitution's "new abstractions MUST be justified by a concrete requirement").
- The "changed assembled payload is rechecked before submission" guarantee (FR-32) is not a
  single shared function either: it is a structural property of where each adapter places its
  guard (LangChain's `InputGuardMiddleware` registered innermost/closest to the model so every
  model turn is independently checked; Microsoft's `MicrosoftChatGuard` firing on every chat
  call; LangGraph's guarded model node running on every graph step that reaches it).
- A caller-supplied middleware/provider mutating content *before* the guard's placement is
  still observed and checked because of that placement (see
  `tests/integration/test_langchain.py::test_user_middleware_mutation_before_guard_is_still_checked`
  and the Microsoft `_CheckedContextProvider` later-middleware rejection); a mutator placed
  *after* the guard has no supported registration point in any of the three facades.
"""

import asyncio
from collections.abc import Awaitable, Callable

from agent_guard.core.errors import ConfigurationError, IntegrationError
from agent_guard.core.guard import Guard
from agent_guard.core.models import EvaluationContext


def extract_context(selector: Callable[[], EvaluationContext]) -> EvaluationContext:
    """Classify adapter-owned extraction faults without catching protected host work."""
    try:
        context = selector()
    except (ConfigurationError, IntegrationError):
        raise
    except Exception:  # noqa: BLE001 - native state/exception text may be sensitive
        raise IntegrationError("native_extraction_failed") from None
    if not isinstance(context, EvaluationContext):
        raise IntegrationError("native_extraction_failed")
    return context


async def async_extract_context(
    selector: Callable[[], Awaitable[EvaluationContext]],
) -> EvaluationContext:
    """Async counterpart of `extract_context` for adapters with a native async
    extraction boundary. Cancellation and caller exceptions keep their identity."""
    try:
        context = await selector()
    except (ConfigurationError, IntegrationError):
        raise
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 - native state/exception text may be sensitive
        raise IntegrationError("native_extraction_failed") from None
    if not isinstance(context, EvaluationContext):
        raise IntegrationError("native_extraction_failed")
    return context


def require_prepared_guard(guard: Guard) -> None:
    """Reject a native registration whose shared guard cannot protect work."""
    if not guard._prepared or guard._closed:
        raise ConfigurationError("guard_not_prepared")
