"""Data-only interpretation for retained DIASI generations.

This module deliberately does not import or execute cutover, PES, or CERS code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256


SUPPORTED_SCHEMAS = frozenset(
    {
        "ovc-diasi-programme-state/v1",
        "ovc-diasi-selected-class-live-route/v1",
        "ovc-vit-qualification-writer-authority/v1",
    }
)


@dataclass(frozen=True)
class HistoricalInterpretation:
    schema: str
    programme_id: str
    lifecycle: str
    route_generation: int | None
    writer_generation: int | None
    old_route_disposition: str | None
    authority_effect: str = "NONE_INTERPRETATION_ONLY"

    @property
    def interpretation_id(self) -> str:
        return canonical_sha256(asdict(self), role="diasi-historical-interpretation/v1")


def interpret_diasi_history(record: Mapping[str, Any]) -> HistoricalInterpretation:
    schema = str(record.get("schema", ""))
    if schema not in SUPPORTED_SCHEMAS:
        raise ValueError(f"DIASI_HISTORY_SCHEMA_UNSUPPORTED:{schema}")
    programme_id = str(record.get("programme_id", "OVC-DIAS-CONFORMANCE-v0.1"))
    if not programme_id:
        raise ValueError("DIASI_HISTORY_PROGRAMME_ID_MISSING")
    route_generation = record.get("route_generation")
    writer_generation = record.get("writer_generation", record.get("generation"))
    for label, value in (("route", route_generation), ("writer", writer_generation)):
        if value is not None and (not isinstance(value, int) or value < 1):
            raise ValueError(f"DIASI_HISTORY_{label.upper()}_GENERATION_INVALID")
    old_route = record.get("old_route", record.get("incumbent_selected_class_status"))
    lifecycle = str(record.get("status", record.get("current_gate", "HISTORICAL")))
    if not lifecycle:
        raise ValueError("DIASI_HISTORY_LIFECYCLE_MISSING")
    return HistoricalInterpretation(
        schema=schema,
        programme_id=programme_id,
        lifecycle=lifecycle,
        route_generation=route_generation,
        writer_generation=writer_generation,
        old_route_disposition=None if old_route is None else str(old_route),
    )
