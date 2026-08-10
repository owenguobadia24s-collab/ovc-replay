from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .manifest import EvidenceStoreError


@dataclass(frozen=True)
class CapacityEnvelope:
    envelope_id: str
    tier: str
    max_external_bytes: int
    max_wall_seconds: float | None = None
    max_peak_rss_bytes: int | None = None

    def assert_external_bytes(self, projected_external_bytes: int) -> None:
        projected = int(projected_external_bytes)
        if projected > self.max_external_bytes:
            raise EvidenceStoreError(
                "CAPACITY_EXTERNAL_BYTES_EXCEEDED "
                f"tier={self.tier} projected={projected} limit={self.max_external_bytes}"
            )


def project_storage_bytes(
    *,
    completed_bytes: int,
    completed_units: int,
    total_units: int,
    remaining_unit_bounds: Iterable[int] = (),
    reserve_fraction: float = 0.30,
) -> dict[str, int | float]:
    """Produce an evidence-derived storage sizing worksheet.

    The function is execution governance only.  It does not change workload,
    scientific quality, output identity, or authority.
    """
    completed_bytes = int(completed_bytes)
    completed_units = int(completed_units)
    total_units = int(total_units)
    reserve_fraction = float(reserve_fraction)
    if completed_bytes < 0 or completed_units <= 0 or total_units < completed_units:
        raise EvidenceStoreError("invalid storage sizing inputs")
    if reserve_fraction < 0:
        raise EvidenceStoreError("reserve_fraction must be non-negative")
    linear_full = (completed_bytes * total_units + completed_units - 1) // completed_units
    remaining_bound = sum(max(0, int(value)) for value in remaining_unit_bounds)
    conservative_full = max(linear_full, completed_bytes + remaining_bound)
    reserve_bound = int(conservative_full * (1.0 + reserve_fraction) + 0.999999999)
    return {
        "completed_bytes": completed_bytes,
        "completed_units": completed_units,
        "total_units": total_units,
        "linear_full_projection_bytes": linear_full,
        "remaining_bound_bytes": remaining_bound,
        "conservative_full_bound_bytes": conservative_full,
        "reserve_fraction": reserve_fraction,
        "minimum_with_reserve_bytes": reserve_bound,
    }
