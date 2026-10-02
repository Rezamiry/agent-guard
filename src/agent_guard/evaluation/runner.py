"""Sequential saved-answer evaluation through the shared guard."""

from dataclasses import dataclass

from agent_guard.core.errors import AgentGuardError, ConfigurationError
from agent_guard.core.guard import Guard
from agent_guard.core.models import BoundaryDecision
from agent_guard.evaluation.dataset import DatasetLineError, SavedExample


@dataclass(frozen=True)
class OfflineResult:
    example_id: str | None
    policy_id: str
    output_decision: BoundaryDecision | None
    error_category: str | None = None
    line_number: int | None = None
    settings_id: str | None = None


def run_saved(guard: Guard, rows: tuple[SavedExample | DatasetLineError, ...]) -> tuple[OfflineResult, ...]:
    if not guard._prepared or guard._closed:
        raise ConfigurationError("guard_not_prepared")
    results: list[OfflineResult] = []
    for row in rows:
        if isinstance(row, DatasetLineError):
            results.append(OfflineResult(None, guard.policy.id, None, row.reason_code,
                                         row.line_number, guard.policy.settings_id))
            continue
        try:
            decision = guard.evaluate_output(row.context)
            results.append(OfflineResult(row.example_id, guard.policy.id, decision,
                                         settings_id=guard.policy.settings_id))
        except AgentGuardError as exc:
            results.append(OfflineResult(row.example_id, guard.policy.id, None,
                                         exc.reason_code,
                                         settings_id=guard.policy.settings_id))
    return tuple(results)
