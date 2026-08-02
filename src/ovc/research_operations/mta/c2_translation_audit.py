from __future__ import annotations

from typing import Any, Mapping

AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
EXPECTED_ROLE_COUNTS = {"BAR_PARENT_EVENT": 2, "C1": 4, "C2_STATE": 6, "C2_TRANSITION": 6}
EXPECTED_ACCOUNTING = {
    "c1_scope_consumptions": 9420,
    "c2_states_total": 9420,
    "c2_states_target": 8598,
    "c2_transitions_total": 7345,
    "c2_transitions_target": 6783,
    "accepted_c2_ids_reconstructed": 16765,
    "unaccounted_c2_records": 0,
}


class MTAWP3AuditError(ValueError):
    """Raised when frozen MTA-WP3 evidence violates an invariant."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise MTAWP3AuditError(marker)


def _role(path: str) -> str:
    if path.startswith("payload/bars/2H_A_L/"):
        return "BAR_PARENT_EVENT"
    if path.startswith("payload/c1/"):
        return "C1"
    if path.startswith("payload/c2/states/"):
        return "C2_STATE"
    if path.startswith("payload/c2/transitions/"):
        return "C2_TRANSITION"
    return "UNKNOWN"


def validate_reference(reference: Mapping[str, Any]) -> dict[str, Any]:
    _require(reference.get("schema") == "ovc-mta-wp3-c2-translation-audit-reference/v1", "REFERENCE_SCHEMA_MISMATCH")
    _require(
        (reference.get("programme_id"), reference.get("packet_id"), reference.get("gate_id"))
        == ("OVC-MTA-v0.2", "MTA-WP3", "MTA-G3"),
        "REFERENCE_IDENTITY_MISMATCH",
    )
    _require(reference.get("plan_version") == "0.2", "REFERENCE_PLAN_VERSION_MISMATCH")

    files = reference.get("input_files")
    _require(isinstance(files, list) and len(files) == 18, "REFERENCE_INPUT_FILE_COUNT_MISMATCH")
    paths: set[str] = set()
    counts = {key: 0 for key in EXPECTED_ROLE_COUNTS}
    for item in files:
        _require(isinstance(item, dict), "REFERENCE_INPUT_FILE_ENTRY_INVALID")
        path = item.get("path")
        _require(isinstance(path, str) and path and path not in paths, "REFERENCE_INPUT_PATH_INVALID")
        paths.add(path)
        role = _role(path)
        _require(role in counts, f"REFERENCE_INPUT_ROLE_INVALID:{path}")
        counts[role] += 1
        _require(isinstance(item.get("size_bytes"), int) and item["size_bytes"] > 0, "REFERENCE_INPUT_SIZE_INVALID")
        _require(isinstance(item.get("record_count"), int) and item["record_count"] > 0, "REFERENCE_INPUT_RECORD_COUNT_INVALID")
        _require(isinstance(item.get("sha256"), str) and len(item["sha256"]) == 64, "REFERENCE_INPUT_SHA256_INVALID")
    _require(counts == EXPECTED_ROLE_COUNTS, "REFERENCE_INPUT_ROLE_MATRIX_MISMATCH")

    artifact = reference.get("external_artifact")
    _require(isinstance(artifact, dict), "REFERENCE_EXTERNAL_ARTIFACT_MISSING")
    _require(artifact.get("provider") == "GOOGLE_DRIVE", "REFERENCE_EXTERNAL_PROVIDER_MISMATCH")
    _require(isinstance(artifact.get("file_id"), str) and artifact["file_id"], "REFERENCE_EXTERNAL_FILE_ID_MISSING")
    _require(isinstance(artifact.get("size_bytes"), int) and artifact["size_bytes"] > 0, "REFERENCE_EXTERNAL_SIZE_INVALID")
    for key in ("sha256", "logical_sha256"):
        _require(isinstance(artifact.get(key), str) and len(artifact[key]) == 64, f"REFERENCE_EXTERNAL_{key.upper()}_INVALID")

    accounting = reference.get("record_accounting")
    _require(accounting == EXPECTED_ACCOUNTING, "REFERENCE_ACCOUNTING_MISMATCH")
    _require(
        accounting["accepted_c2_ids_reconstructed"] == accounting["c2_states_total"] + accounting["c2_transitions_total"],
        "REFERENCE_RECONSTRUCTED_ID_ACCOUNTING_MISMATCH",
    )

    statuses = reference.get("target_axis_status")
    _require(isinstance(statuses, dict) and tuple(statuses) == AXES, "REFERENCE_AXIS_STATUS_SHAPE_MISMATCH")
    for axis in AXES:
        _require(isinstance(statuses.get(axis), dict), f"REFERENCE_AXIS_STATUS_MISSING:{axis}")
        _require(sum(statuses[axis].values()) == 8598, f"REFERENCE_AXIS_DENOMINATOR_MISMATCH:{axis}")
    expected_warmup = {"EVALUATED": 4996, "NOT_EVALUATED": 3602}
    for axis in ("LOCATION", "MOTION", "ORGANISATION"):
        _require(statuses[axis] == expected_warmup, f"REFERENCE_WARMUP_AXIS_MISMATCH:{axis}")
    _require(statuses["QUALITY"] == {"EVALUATED": 8598}, "REFERENCE_QUALITY_STATUS_MISMATCH")

    values = reference.get("target_axis_values")
    _require(isinstance(values, dict), "REFERENCE_TARGET_AXIS_VALUES_MISSING")
    _require(values.get("QUALITY") == {"CENSORED": 3602, "DEGRADED": 4996}, "REFERENCE_QUALITY_VALUE_MISMATCH")

    structural = reference.get("target_structural_outcomes")
    _require(isinstance(structural, dict) and isinstance(structural.get("container"), dict), "REFERENCE_TARGET_CONTAINER_MISSING")
    _require(
        structural["container"].get("PARENT_RANGE|EXCLUDED|MISSING_FIRST_VALID_BOUNDARY") == 8598,
        "REFERENCE_PARENT_RANGE_ACCOUNTING_MISMATCH",
    )

    mismatches = reference.get("mismatch_counts")
    _require(isinstance(mismatches, dict), "REFERENCE_MISMATCH_COUNTS_MISSING")
    _require(all(value == 0 for value in mismatches.values()), "REFERENCE_MISMATCHES_NONZERO")

    findings = reference.get("findings")
    _require(isinstance(findings, list), "REFERENCE_FINDINGS_MISSING")
    finding_ids = {item.get("finding_id") for item in findings if isinstance(item, dict)}
    required_findings = {"MTA-WP3-F1", "MTA-WP3-F2", "MTA-WP3-F3", "MTA-WP3-F4"}
    _require(required_findings.issubset(finding_ids), "REFERENCE_FINDING_SET_MISMATCH")
    _require(reference.get("qa_recommendation") == "PASS_WITH_MATERIAL_FINDINGS", "REFERENCE_QA_NOT_PASS")

    denied = {
        "selector_change": "DENIED",
        "formula_threshold_change": "DENIED",
        "clock_change": "DENIED",
        "c2e_c2_5_c3": "DENIED",
        "validation_consumption": "DENIED",
        "r2_publication": "DENIED",
        "probability_risk_exposure_execution": "NONE",
    }
    for key, expected in denied.items():
        _require(reference.get(key) == expected, f"REFERENCE_AUTHORITY_ESCAPE:{key}")

    return {
        "status": "PASS",
        "input_file_count": 18,
        "c2_states_total": accounting["c2_states_total"],
        "c2_transitions_total": accounting["c2_transitions_total"],
        "accepted_c2_ids_reconstructed": accounting["accepted_c2_ids_reconstructed"],
        "external_artifact_sha256": artifact["sha256"],
        "material_findings": sorted(finding_ids),
    }


def validate_sequence_fixture(fixture: Mapping[str, Any]) -> dict[str, Any]:
    _require(fixture.get("schema") == "ovc-mta-wp3-sequence-fixture/v1", "FIXTURE_SCHEMA_MISMATCH")
    states = fixture.get("states")
    transitions = fixture.get("transitions")
    _require(isinstance(states, list) and states, "FIXTURE_STATES_MISSING")
    _require(isinstance(transitions, list), "FIXTURE_TRANSITIONS_MISSING")

    by_id: dict[str, Mapping[str, Any]] = {}
    order: list[str] = []
    for state in states:
        _require(isinstance(state, dict), "FIXTURE_STATE_INVALID")
        state_id = state.get("c2_state_id")
        _require(isinstance(state_id, str) and state_id.startswith("c2-state:"), "FIXTURE_STATE_ID_INVALID")
        _require(state_id not in by_id, "FIXTURE_DUPLICATE_STATE_ID")
        _require(tuple(state.get("axes", {})) == AXES, "FIXTURE_AXIS_SHAPE_MISMATCH")
        persistence = state.get("persistence")
        _require(isinstance(persistence, dict) and tuple(persistence) == AXES, "FIXTURE_PERSISTENCE_SHAPE_MISMATCH")
        _require(all(isinstance(value, int) and value > 0 for value in persistence.values()), "FIXTURE_PERSISTENCE_INVALID")
        _require(state.get("continuity") in {"RESET", "CONTIGUOUS"}, "FIXTURE_CONTINUITY_INVALID")
        by_id[state_id] = state
        order.append(state_id)

    for transition in transitions:
        _require(isinstance(transition, dict), "FIXTURE_TRANSITION_INVALID")
        source = transition.get("from_state_id")
        target = transition.get("to_state_id")
        _require(source in by_id and target in by_id, "FIXTURE_TRANSITION_ENDPOINT_MISSING")
        _require(order.index(source) < order.index(target), "FIXTURE_TRANSITION_ORDER_INVALID")
        changed = transition.get("changed_axes")
        _require(isinstance(changed, list) and changed and len(changed) == len(set(changed)), "FIXTURE_CHANGED_AXES_INVALID")
        observed = sorted(axis for axis in AXES if by_id[source]["axes"][axis] != by_id[target]["axes"][axis])
        _require(sorted(changed) == observed, "FIXTURE_CHANGED_AXES_MISMATCH")

    return {"status": "PASS", "states": len(states), "transitions": len(transitions)}
