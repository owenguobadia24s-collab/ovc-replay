from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, seal_object


def build_estimand_denominator(*, estimand: str, universe_id: str) -> dict[str, Any]:
    if estimand not in {"REFERENCE_BOUNDARY_AUDIT", "CONSENSUS_BOUNDARY_DISCOVERY"} or not universe_id:
        raise CBSContractError("CBS_ESTIMAND_DENOMINATOR_INVALID")
    return seal_object({"schema":"ovc-cbs-estimand-denominator/v0.1","estimand":estimand,
        "evaluation_universe_id":universe_id,"positive_only":False},id_field="denominator_id")


def build_reference_boundary_audit(*, b0_projection_id: str, region_set: Mapping[str, Any],
                                   denominator: Mapping[str, Any], ledger_ids: Sequence[str]) -> dict[str, Any]:
    if region_set.get("estimand") != "REFERENCE_BOUNDARY_AUDIT" or denominator.get("estimand") != "REFERENCE_BOUNDARY_AUDIT":
        raise CBSContractError("ESTIMAND_CROSSING")
    if region_set.get("estimand_denominator_id") != denominator.get("denominator_id"):
        raise CBSContractError("CBS_ESTIMAND_DENOMINATOR_MISMATCH")
    return seal_object({"schema":"ovc-cbs-reference-boundary-audit/v0.1","estimand":"REFERENCE_BOUNDARY_AUDIT",
        "b0_projection_id":b0_projection_id,"region_set_id":region_set["region_set_id"],
        "denominator_id":denominator["denominator_id"],"correspondence_ledger_ids":sorted(ledger_ids),
        "consensus_discovery_effect":"NONE","ground_truth":False},id_field="reference_boundary_audit_id")


def build_consensus_boundary_discovery(*, region_set: Mapping[str, Any], denominator: Mapping[str, Any],
                                       ledger_ids: Sequence[str]) -> dict[str, Any]:
    if region_set.get("estimand") != "CONSENSUS_BOUNDARY_DISCOVERY" or denominator.get("estimand") != "CONSENSUS_BOUNDARY_DISCOVERY":
        raise CBSContractError("ESTIMAND_CROSSING")
    if region_set.get("estimand_denominator_id") != denominator.get("denominator_id"):
        raise CBSContractError("CBS_ESTIMAND_DENOMINATOR_MISMATCH")
    return seal_object({"schema":"ovc-cbs-consensus-boundary-discovery/v0.1","estimand":"CONSENSUS_BOUNDARY_DISCOVERY",
        "region_set_id":region_set["region_set_id"],"denominator_id":denominator["denominator_id"],
        "correspondence_ledger_ids":sorted(ledger_ids),"privileged_method":None,"ground_truth":False},
        id_field="consensus_boundary_discovery_id")


def assert_estimand_separation(audit: Mapping[str, Any], discovery: Mapping[str, Any]) -> None:
    if audit.get("denominator_id") == discovery.get("denominator_id"):
        raise CBSContractError("ESTIMAND_CROSSING:SHARED_DENOMINATOR")
    if set(audit.get("correspondence_ledger_ids", [])) & set(discovery.get("correspondence_ledger_ids", [])):
        raise CBSContractError("ESTIMAND_CROSSING:SHARED_LEDGER")
