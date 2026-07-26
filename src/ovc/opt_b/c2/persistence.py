from __future__ import annotations

from typing import Any, Mapping


def apply_persistence(current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(current)
    persisted: dict[str, int] = {}
    contiguous = bool(previous) and all(
        previous.get(k) == current.get(k)
        for k in ("c1_release_id", "clock", "side", "evaluation_scope_id", "parameter_pack_id")
    )
    for axis, payload in current["axes"].items():
        count = 1
        if contiguous and previous and previous.get("axes", {}).get(axis) == payload:
            count = int(previous.get("persistence", {}).get(axis, 1)) + 1
        persisted[axis] = count
    out["persistence"] = persisted
    out["continuity"] = "CONTIGUOUS" if contiguous else "RESET"
    return out
