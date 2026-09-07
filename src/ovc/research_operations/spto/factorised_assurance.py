"""Independent blocking assurance for the WP6 factorised mechanics packet."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .factorised_mechanics import (
    ANTECEDENT_HIERARCHIES,
    CARRIER_FIELDS,
    DECLARED_REPRESENTATIONS,
    PROTOCOL_SHA256,
    build_carrier_view,
    build_operation_view,
    content_id,
    project_frontier_to_comparison_target,
    select_antecedent_backoff,
    select_target_resolution,
    synthetic_qualification_fixture,
)


ASSURANCE_VERSION = "C2S-SPTOI-WP7-INDEPENDENT-ALGORITHMIC-ASSURANCE-v1"


class AssuranceFailure(RuntimeError):
    def __init__(self, check_id: str, detail: str):
        super().__init__(f"{check_id}: {detail}")
        self.check_id = check_id
        self.detail = detail


def _load(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _pass(check_id: str, assertion: str, evidence: Any) -> dict[str, Any]:
    return {"check_id": check_id, "assertion": assertion, "result": "PASS", "evidence": evidence}


def _assert(check_id: str, condition: bool, detail: str) -> None:
    if not condition:
        raise AssuranceFailure(check_id, detail)


def build_algorithmic_assurance_receipt(root: Path) -> dict[str, Any]:
    registry = _load(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_FACTORISED_MECHANICS_REGISTRY_v0_1.json",
    )
    fixture = _load(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_SYNTHETIC_QUALIFICATION_FIXTURE_v0_1.json",
    )
    owner = _load(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_C2_OWNER_STREAM_BINDING_v0_1.json",
    )
    factor_source = _load(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_FACTORISED_SOURCE_BINDING_MANIFEST_v0_1.json",
    )
    c0c = _load(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.json",
    )
    dense = _load(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_FACTORISED_DENSE_MICRO_SOURCE_SCOPE_BINDING_v0_1.json",
    )
    checks: list[dict[str, Any]] = []

    registry_body = copy.deepcopy(registry)
    registry_id = registry_body.pop("registry_id")
    _assert(
        "WP7-ALG-01",
        registry_id == content_id("FactorisedMechanicsRegistry/v1", registry_body),
        "registry content identity mismatch",
    )
    checks.append(_pass("WP7-ALG-01", "REGISTRY_CANONICAL_IDENTITY_REBUILDS", registry_id))

    fixture_body = copy.deepcopy(fixture)
    fixture_id = fixture_body.pop("bundle_id")
    rebuilt_fixture = synthetic_qualification_fixture()
    _assert(
        "WP7-ALG-02",
        fixture_id == content_id("FactorisedMechanicsSyntheticFixture/v1", fixture_body)
        and rebuilt_fixture == fixture,
        "synthetic fixture rebuild differs",
    )
    checks.append(_pass("WP7-ALG-02", "FRESH_REBUILD_EQUALS_FILED_FIXTURE", fixture_id))

    _assert(
        "WP7-ALG-03",
        owner["record_policy"] == "EXACT_OWNER_RECORDS_PRESERVED_NO_FLATTENING_NO_REPAIR"
        and factor_source["primary_source"]["role"] == "REQUIRED_PRIMARY_STATE_TARGET_SPINE"
        and factor_source["secondary_source"]["status"] == "REQUIRED_NOT_YET_BOUND_WP6"
        and dense["exact_dense_source_binding"] is None
        and dense["factorised_real_source_execution_eligible"] is False,
        "source role or fail-closed dense-source state changed",
    )
    checks.append(
        _pass(
            "WP7-ALG-03",
            "OWNER_PRIMARY_AND_DENSE_SECONDARY_SOURCE_BOUNDARY_PRESERVED",
            "EXACT_DENSE_SOURCE_PENDING_NO_SUBSTITUTION",
        )
    )

    _assert(
        "WP7-ALG-04",
        c0c["join_eligibility"] is False
        and c0c["concordance_state"] == "RECEIPT_CONCORDANT_NOT_BYTE_REPRODUCED",
        "C0C cross-export join was promoted",
    )
    checks.append(_pass("WP7-ALG-04", "C0C_CROSS_EXPORT_JOIN_REMAINS_DENIED", c0c["concordance_state"]))

    vector = {
        "ENV_STATUS": ("OPEN", "OPEN"),
        "ENV_LIFECYCLE": ("FORMING", "MATURE"),
        "ENV_RELATION": ("INSIDE", "INSIDE"),
        "ETR_ATOMIC": ("UP", "DOWN"),
        "ETR_COMPOUND": ("EXPAND", "EXPAND"),
        "ETR_OPEN_STATE": ("OPEN", "CLOSED"),
    }
    expected_exact = (
        ("ENV_STATUS", "OPEN"),
        ("ENV_LIFECYCLE", "CHANGED"),
        ("ENV_RELATION", "INSIDE"),
        ("ETR_ATOMIC", "CHANGED"),
        ("ETR_COMPOUND", "EXPAND"),
        ("ETR_OPEN_STATE", "CHANGED"),
    )
    exact = build_carrier_view("ASSURE.OCC", "C_EXACT_v1", vector)
    hi = build_carrier_view("ASSURE.OCC", "R25_HI_v1", vector)
    mid = build_carrier_view("ASSURE.OCC", "R25_MID_v1", vector)
    _assert(
        "WP7-ALG-05",
        exact is not None and exact.values == expected_exact
        and hi is not None and dict(hi.values)["ETR_COMPOUND"] == "UNCHANGED"
        and mid is not None and dict(mid.values)["ETR_ATOMIC"] == "CHANGED",
        "carrier decoder differs from independent truth vector",
    )
    checks.append(_pass("WP7-ALG-05", "FACTOR_DECODER_EXACT_HI_MID_TRUTH_VECTOR", exact.carrier_morphology_id))

    operation = build_operation_view(
        "ASSURE.OCC", {"COUNT_A": -1, "COUNT_B": 0, "COUNT_C": 1},
        {"ENUM_A": ("X", "X"), "ENUM_B": ("X", "Y")},
    )
    _assert(
        "WP7-ALG-06",
        operation.count_roles == (("COUNT_A", -1), ("COUNT_B", 0), ("COUNT_C", 1))
        and operation.enum_roles == (("ENUM_A", "UNCHANGED"), ("ENUM_B", "CHANGED"))
        and set(CARRIER_FIELDS) == set(registry["carrier_packs"]["C_EXACT_v1"]["exact_fields"]),
        "carrier/operation pack builder mismatch",
    )
    checks.append(_pass("WP7-ALG-06", "CARRIER_AND_OPERATION_PACK_BUILDERS_EXACT", operation.operation_morphology_id))

    support_map = {"EXACT": 1, "HI": 2, "MID": 5, "PATH": 3, "OP": 8}
    expected_backoff = {"BASE": "HI", "NO_HI": "MID", "NO_MID": "HI", "PATH_BEFORE_MID": "HI", "NO_PATH": "HI"}
    actual_backoff = {
        hierarchy: select_antecedent_backoff(hierarchy, support_map)[0]
        for hierarchy in ANTECEDENT_HIERARCHIES
    }
    _assert("WP7-ALG-07", actual_backoff == expected_backoff, repr(actual_backoff))
    checks.append(_pass("WP7-ALG-07", "ALL_ANTECEDENT_HIERARCHY_REDUCERS_MATCH_ORACLE", actual_backoff))

    relation_supports = {"T0_v1": 1, "T1_v1": 1, "R18_MID_v1": 2, "ETR_v1": 4, "T2_v1": 5, "T3_v1": 8}
    expected_target = {"BASE": "R18_MID_v1", "NO_T1": "R18_MID_v1", "NO_MID": "ETR_v1", "NO_ETR": "R18_MID_v1", "COMPACT": "R18_MID_v1"}
    actual_target = {
        hierarchy: select_target_resolution(hierarchy, relation_supports)[0]
        for hierarchy in registry["target_hierarchies"]
    }
    _assert("WP7-ALG-08", actual_target == expected_target, repr(actual_target))
    checks.append(_pass("WP7-ALG-08", "ALL_TARGET_HIERARCHY_REDUCERS_MATCH_ORACLE", actual_target))

    projected = project_frontier_to_comparison_target(
        "T1_v1", {"fine-a": 2, "fine-b": 3, "fine-c": 1},
        {"fine-a": "mid-x", "fine-b": "mid-x", "fine-c": "mid-y"},
    )
    _assert("WP7-ALG-09", projected == (("mid-x", 5), ("mid-y", 1)), repr(projected))
    checks.append(_pass("WP7-ALG-09", "COMMON_TARGET_PROJECTION_AGGREGATES_SUPPORT_EXACTLY", projected))

    support_rows = {
        row["representation_id"]: tuple((target, count) for target, count in row["target_supports"])
        for row in fixture["frontier_records"]
    }
    _assert(
        "WP7-ALG-10",
        tuple(support_rows) == DECLARED_REPRESENTATIONS
        and all(row["opportunity_denominator"] == 2 for row in fixture["frontier_records"]),
        "support maps or denominators were dropped",
    )
    checks.append(_pass("WP7-ALG-10", "RELATION_SUPPORT_MAPS_AND_DENOMINATORS_LOSSLESS", support_rows))

    qualified = {
        representation: {target for target, count in supports if count >= 2}
        for representation, supports in support_rows.items()
    }
    core = set.intersection(*(set(value) for value in qualified.values()))
    envelope = set.union(*(set(value) for value in qualified.values()))
    shell = envelope - core
    _assert(
        "WP7-ALG-11",
        sorted(core) == fixture["robust_frontier"]["members"]
        and sorted(shell) == fixture["ambiguity_shell"]["members"],
        "declared-set geometry differs from independent set reducer",
    )
    checks.append(_pass("WP7-ALG-11", "DECLARED_SET_CORE_AND_SHELL_MATCH_INDEPENDENT_REDUCER", {"core": sorted(core), "shell": sorted(shell)}))

    state = fixture["state_core"]
    independent_axes = {
        "antecedent_support_min": min(row["antecedent_support"] for row in fixture["frontier_records"]),
        "backoff_level_set": sorted({row["selected_backoff_level"] for row in fixture["frontier_records"]}),
        "robust_core_size": len(core),
        "ambiguity_shell_size": len(shell),
        "target_resolution_set": sorted({row["selected_target_resolution"] for row in fixture["frontier_records"]}),
    }
    _assert(
        "WP7-ALG-12",
        all(state[key] == value for key, value in independent_axes.items()) and "confidence" not in state,
        "five-axis state compression mismatch",
    )
    checks.append(_pass("WP7-ALG-12", "FIVE_AXIS_STATE_COMPRESSION_MATCHES_ORACLE", independent_axes))

    traces = fixture["trace_set"]["traces"]
    _assert(
        "WP7-ALG-13",
        fixture["trace_set"]["complete"] is True
        and [trace["representation_id"] for trace in traces] == list(DECLARED_REPRESENTATIONS)
        and [trace["frontier_record"]["record_id"] for trace in traces]
        == [row["record_id"] for row in fixture["frontier_records"]],
        "TraceSet replay lost or reordered a view",
    )
    checks.append(_pass("WP7-ALG-13", "TRACE_SET_REPLAYS_ALL_FRONTIER_RECORDS_IN_FROZEN_ORDER", fixture["trace_set"]["trace_set_id"]))

    _assert(
        "WP7-ALG-14",
        fixture["derivation_manifest"]["dependency_closure_complete"] is True
        and fixture["realised_continuation_in_prospective_identity"] is False,
        "derivation closure or prospective firewall failed",
    )
    checks.append(_pass("WP7-ALG-14", "DERIVATION_CLOSURE_AND_PROSPECTIVE_IDENTITY_FIREWALL", fixture["derivation_manifest"]["manifest_id"]))

    receipt = {
        "schema": "ovc-c2s-sptoi-rich-algorithmic-assurance-receipt/v0.1",
        "assurance_version": ASSURANCE_VERSION,
        "programme_id": "OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1",
        "packet_id": "C2S-SPTOI-WP7",
        "gate_id": "C2S-SPTOI-G7-RICH-ALG",
        "protocol_sha256": PROTOCOL_SHA256,
        "wp6_registry_id": registry_id,
        "wp6_fixture_bundle_id": fixture_id,
        "checks": checks,
        "check_count": len(checks),
        "result": "PASS_SOURCE_FREE_ALGORITHMIC_ASSURANCE",
        "fresh_process_requirement": "VERIFIED_BY_RUNNER_REEXECUTION_TEST",
        "protected_source_access": "NONE",
        "factorised_evidence_execution": "DENIED",
        "authority_effect": "NONE_ALGORITHMIC_ASSURANCE_ONLY",
    }
    receipt = json.loads(json.dumps(receipt, sort_keys=True))
    receipt["receipt_id"] = content_id("RichAlgorithmicAssuranceReceipt/v1", receipt)
    return receipt
