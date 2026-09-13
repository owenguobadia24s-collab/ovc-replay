from __future__ import annotations

from copy import deepcopy
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .mechanical import BCWTValidationError, TERMINAL_STATUSES, logical_id

BCWT_RECORD_DIRECTORIES = {
    "BCWT_B_TO_C_ORIGIN.v0.1": "bcwt/origins",
    "BCWT_CONSEQUENCE_MEASUREMENT_PACK.v0.1": "bcwt/consequence_packs",
    "BCWT_OUTCOME_JOIN_MANIFEST.v0.1": "bcwt/join_manifests",
    "BCWT_OUTCOME_RECORD.v0.1": "bcwt/outcomes",
    "BCWT_OUTCOME_LEDGER.v0.1": "bcwt/ledgers",
    "BCWT_MECHANICAL_RUN_RECEIPT.v0.1": "bcwt/run_receipts",
}
BCWT_RECORD_TYPES = frozenset(BCWT_RECORD_DIRECTORIES)
BCWT_PAYLOAD_REQUIRED = {
    "BCWT_B_TO_C_ORIGIN.v0.1": {
        "schema", "logical_id", "origin_contract_id", "reference_id", "observer_state_id",
        "observer_generation", "segment_id", "origin_cutoff_fvt_ms", "input_prefix_chain_sha256",
        "shared_fixed_asset_set_id", "source_population_ref", "state_row_sha256", "component_status_map",
        "epistemic_non_knowledge", "source_break_state", "candidate_generation_id_or_none",
        "candidate_occurrence_id_or_none", "candidate_evaluation_admission_id_or_none", "origin_role",
        "authority_effect", "scientific_effect",
    },
    "BCWT_CONSEQUENCE_MEASUREMENT_PACK.v0.1": {
        "schema", "consequence_pack_id", "version", "source_binding", "price_side_policy", "path_clock",
        "anchor_specs", "fixed_horizons_observed_bars", "measurement_specs", "structural_consequence_specs",
        "censoring_rules", "gap_rules", "missingness_rules", "prohibited_semantics",
        "created_before_payload_access", "authority_effect", "scientific_effect", "fixture_only",
    },
    "BCWT_OUTCOME_JOIN_MANIFEST.v0.1": {
        "schema", "logical_id", "execution_role", "candidate_generation_id_or_none",
        "candidate_population_binding_or_none", "candidate_occurrence_set_hash_or_none",
        "candidate_evaluation_admission_id_or_none", "mechanical_origin_set_hash", "origin_contract_id",
        "reference_id", "consequence_pack_id", "source_release_ref", "instrument", "side", "clock",
        "anchor_spec_id", "censoring_policy_id", "authority_effect", "scientific_effect",
    },
    "BCWT_OUTCOME_RECORD.v0.1": {
        "schema", "logical_id", "origin_id", "observer_state_id", "consequence_pack_id",
        "join_manifest_id", "anchor_spec_id", "horizon_observed_bars", "measurement_spec_id",
        "terminal_status", "measurement_state", "value", "authority_effect", "scientific_effect",
    },
    "BCWT_OUTCOME_LEDGER.v0.1": {
        "schema", "logical_id", "join_manifest_id", "consequence_pack_id", "expected_rows", "actual_rows",
        "terminal_status_counts", "records", "authority_effect", "scientific_effect",
    },
    "BCWT_MECHANICAL_RUN_RECEIPT.v0.1": {
        "schema", "run_receipt_id", "execution_role", "reference_id", "consequence_pack_id",
        "join_manifest_id", "origin_count", "expected_rows", "actual_rows", "terminal_status_counts",
        "replay_digest", "authority_effect", "scientific_effect",
    },
}


def _require_none_effect(payload: dict[str, Any]) -> None:
    if payload.get("authority_effect") != "NONE" or payload.get("scientific_effect") != "NONE":
        raise BCWTValidationError("BCWT-R2 payload must have authority_effect/scientific_effect NONE")


def _assert_no_scientific_refs(payload: dict[str, Any]) -> None:
    for key in (
        "candidate_generation_id_or_none",
        "candidate_occurrence_id_or_none",
        "candidate_population_binding_or_none",
        "candidate_occurrence_set_hash_or_none",
        "candidate_evaluation_admission_id_or_none",
    ):
        if key in payload and payload.get(key) is not None:
            raise BCWTValidationError(f"BCWT-R2 scientific reference forbidden: {key}")


def validate_bcwt_payload(record_type: str, payload: dict[str, Any]) -> None:
    if record_type not in BCWT_RECORD_TYPES:
        raise BCWTValidationError(f"unknown BCWT record type: {record_type}")
    missing = BCWT_PAYLOAD_REQUIRED[record_type] - set(payload)
    if missing:
        raise BCWTValidationError(f"missing BCWT payload fields: {','.join(sorted(missing))}")
    _require_none_effect(payload)
    if record_type == "BCWT_B_TO_C_ORIGIN.v0.1":
        if payload.get("schema") != "ovc-bcwt-b-to-c-origin/v0_1":
            raise BCWTValidationError("origin schema mismatch")
        if payload.get("origin_role") != "MECHANICAL_REFERENCE_ORIGIN":
            raise BCWTValidationError("BCWT-R2 persists mechanical origins only")
        _assert_no_scientific_refs(payload)
        if payload.get("logical_id") != logical_id("origin", payload):
            raise BCWTValidationError("origin logical_id mismatch")
        return
    if record_type == "BCWT_CONSEQUENCE_MEASUREMENT_PACK.v0.1":
        if payload.get("schema") != "ovc-bcwt-consequence-measurement/v0_1":
            raise BCWTValidationError("consequence pack schema mismatch")
        if payload.get("created_before_payload_access") is not True:
            raise BCWTValidationError("consequence pack must be frozen before payload access")
        horizons = payload.get("fixed_horizons_observed_bars")
        if not isinstance(horizons, list) or not horizons or len(set(horizons)) != len(horizons):
            raise BCWTValidationError("invalid/duplicate horizon set")
        material = deepcopy(payload)
        material["consequence_pack_id"] = "PENDING_HASH"
        expected = logical_id("consequence_pack", material)
        if payload.get("consequence_pack_id") != expected:
            raise BCWTValidationError("consequence_pack_id mismatch")
        return
    if record_type == "BCWT_OUTCOME_JOIN_MANIFEST.v0.1":
        if payload.get("schema") != "ovc-bcwt-outcome-join-manifest/v0_1":
            raise BCWTValidationError("join schema mismatch")
        if payload.get("execution_role") != "MECHANICAL_REFERENCE_ONLY":
            raise BCWTValidationError("BCWT-R2 persists mechanical join manifests only")
        _assert_no_scientific_refs(payload)
        if payload.get("logical_id") != logical_id("join", payload):
            raise BCWTValidationError("join logical_id mismatch")
        return
    if record_type == "BCWT_OUTCOME_RECORD.v0.1":
        if payload.get("schema") != "ovc-bcwt-outcome-record/v0_1":
            raise BCWTValidationError("outcome schema mismatch")
        if payload.get("terminal_status") not in TERMINAL_STATUSES:
            raise BCWTValidationError("unknown outcome terminal status")
        if payload.get("logical_id") != logical_id("outcome", payload):
            raise BCWTValidationError("outcome logical_id mismatch")
        return
    if record_type == "BCWT_OUTCOME_LEDGER.v0.1":
        if payload.get("schema") != "ovc-bcwt-outcome-ledger/v0_1":
            raise BCWTValidationError("ledger schema mismatch")
        if payload.get("expected_rows") != payload.get("actual_rows"):
            raise BCWTValidationError("ledger denominator incomplete")
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != payload.get("actual_rows"):
            raise BCWTValidationError("ledger row list/count mismatch")
        keys = {
            (row.get("origin_id"), row.get("horizon_observed_bars"), row.get("measurement_spec_id"))
            for row in records
        }
        if len(keys) != payload.get("expected_rows"):
            raise BCWTValidationError("ledger duplicate/missing keys")
        if payload.get("logical_id") != logical_id("ledger", payload):
            raise BCWTValidationError("ledger logical_id mismatch")
        return
    if record_type == "BCWT_MECHANICAL_RUN_RECEIPT.v0.1":
        if payload.get("schema") != "ovc-bcwt-mechanical-run-receipt/v0_1":
            raise BCWTValidationError("run receipt schema mismatch")
        if payload.get("execution_role") != "MECHANICAL_REFERENCE_ONLY":
            raise BCWTValidationError("scientific run receipt forbidden")
        if payload.get("expected_rows") != payload.get("actual_rows"):
            raise BCWTValidationError("run receipt denominator incomplete")
        material = deepcopy(payload)
        material["run_receipt_id"] = "PENDING_HASH"
        expected = f"bcwt:run_receipt:{canonical_sha256(material)}"
        if payload.get("run_receipt_id") != expected:
            raise BCWTValidationError("run_receipt_id mismatch")
        return
    raise BCWTValidationError(f"unhandled BCWT record type: {record_type}")
