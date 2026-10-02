"""Public policy authoring helpers and non-secret settings identity."""

import hashlib
import json

from agent_guard.checks.semantic import RUBRIC_VERSION

from .models import PolicySet


def settings_identity(policy: PolicySet) -> str:
    declared = {
        "schema": 1,
        "policy_id": policy.id,
        "evidence_required": policy.evidence_required,
        "semantic_rubric_version": RUBRIC_VERSION,
        "checks": [
            {
                "id": check.id,
                "kind": check.kind.value,
                "boundary": check.boundary.value,
                "required": check.required,
                "enabled": check.enabled,
                "minimum_confidence": check.minimum_confidence,
                "criteria_present": check.criteria is not None,
                "criteria_revision": check.criteria_revision,
            }
            for check in policy.checks
        ],
    }
    canonical = json.dumps(declared, sort_keys=True, separators=(",", ":"))
    return "settings-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
