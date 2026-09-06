from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..identity import seal_object


def run_b9_control(*, opportunity_count: int, source_events: Sequence[Mapping[str, Any]], config_id: str) -> dict[str, Any]:
    return seal_object({"schema":"ovc-cbs-comparator-output/v0.1","method_id":"B9","config_id":config_id,
        "estimates":[],"opportunity_count":opportunity_count,"no_estimate_count":opportunity_count,
        "typed_source_events":[dict(item) for item in source_events],"source_events_are_method_boundaries":False},
        id_field="output_id")
