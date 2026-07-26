from __future__ import annotations

from typing import Any, Mapping

from .identity import stable_id


def build_transition(current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if previous is None:
        return None
    changed = [axis for axis, value in current["axes"].items() if previous.get("axes", {}).get(axis) != value]
    if not changed:
        return None
    identity = {
        "from": previous["c2_state_id"],
        "to": current["c2_state_id"],
        "changed_axes": sorted(changed),
        "first_valid_time": current["first_valid_time"],
    }
    return {
        "c2_transition_id": stable_id("c2-transition", identity),
        "from_state_id": previous["c2_state_id"],
        "to_state_id": current["c2_state_id"],
        "changed_axes": sorted(changed),
        "first_valid_time": current["first_valid_time"],
        "status": "OBSERVED",
    }
