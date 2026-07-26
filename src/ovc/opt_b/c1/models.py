from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class SourceBar:
    release_id: str
    manifest_id: str
    research_role: str
    instrument_id: str
    clock_id: str
    price_side: str
    source_bar_id: str
    open_time: str
    close_time: str
    first_valid_time: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    price_increment: Decimal | None
    admissibility: str
    quality_state: str
    synthetic: bool
    selector_state: str
    authority_state: str
    validation_consumption_state: str
    parent_source_object_ids: tuple[str, ...]
    parent_m1_bar_ids: tuple[str, ...]


@dataclass(frozen=True)
class C1Result:
    record_id: str
    source_bar_id: str
    release_id: str
    manifest_id: str
    research_role: str
    instrument_id: str
    clock_id: str
    price_side: str
    open_time: str
    close_time: str
    first_valid_time: str
    formula_registry_id: str
    measurements: Mapping[str, str | None]
    categorical: Mapping[str, str]
    null_reasons: Mapping[str, str]
    source_quality_state: str
    synthetic: bool
    authority_state: str = "NONE"
