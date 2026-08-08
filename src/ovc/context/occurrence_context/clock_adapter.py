from __future__ import annotations

from typing import Any

from .builder import OccurrenceContextError

ALLOWED_CLOCKS = {"15M", "2H_A_L"}


def clock_scale_context(*, clock_id: str, scale_id: str | None = None, lattice_id: str | None = None, canonical_clock_position: Any = None) -> dict[str, Any]:
    if clock_id not in ALLOWED_CLOCKS:
        raise OccurrenceContextError("OC_AUTH_NEW_CLOCK_DENIED")
    return {
        "clock_id": clock_id,
        "scale_id": scale_id or clock_id,
        "lattice_id": lattice_id,
        "canonical_clock_position": canonical_clock_position,
        "lattice_authority": "REFERENCE_ONLY_NO_ACTIVATION" if lattice_id else "NONE",
    }
