from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .identity import CBSContractError, seal_object


PROTECTED_SCOPE = ("population", "methods", "configurations", "tolerances", "representations", "nulls", "opportunities")


def build_capacity_receipt(*, declared: Mapping[str, int], executed: Mapping[str, int], capacity_limit: int,
                           retained_artifact_families: list[str], required_artifact_families: list[str]) -> dict[str, Any]:
    if capacity_limit <= 0 or any(name not in declared or name not in executed for name in PROTECTED_SCOPE):
        raise CBSContractError("CAPACITY_EXCEEDED:INCOMPLETE_DECLARATION")
    scope_drops = {name: {"declared": int(declared[name]), "executed": int(executed[name])}
                   for name in PROTECTED_SCOPE if int(executed[name]) != int(declared[name])}
    work = 1
    for name in ("population", "methods", "configurations", "tolerances", "representations", "nulls"):
        work *= max(1, int(declared[name]))
    missing_artifacts = sorted(set(required_artifact_families) - set(retained_artifact_families))
    if scope_drops or work > capacity_limit:
        raise CBSContractError("CAPACITY_EXCEEDED")
    if missing_artifacts:
        raise CBSContractError("ARTIFACT_RETENTION_INCOMPLETE")
    return seal_object(
        {"schema": "ovc-cbs-capacity-receipt/v0.1", "declared_scope": dict(declared),
         "executed_scope": dict(executed), "estimated_work_units": work, "capacity_limit": capacity_limit,
         "retained_artifact_families": sorted(set(retained_artifact_families)), "scope_drops": {},
         "sampling": False, "top_n": False, "capacity_status": "PASS"}, id_field="capacity_receipt_id"
    )
