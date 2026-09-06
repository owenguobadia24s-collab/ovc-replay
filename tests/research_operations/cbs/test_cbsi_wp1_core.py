from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.cbs.contracts import (
    build_research_generation,
    validate_authority_delta,
    validate_comparator_registry,
    validate_estimand_identity,
)
from ovc.research_operations.cbs.enums import Estimand, NON_TRANSITIVITY
from ovc.research_operations.cbs.identity import CBSContractError, canonical_id, seal_object, verify_object


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registries" / "research_operations" / "cbs"
DOCS = ROOT / "docs" / "programmes" / "c2e-boundary-stability-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def test_canonical_identity_is_stable_and_fail_closed() -> None:
    assert canonical_id({"b": 2, "a": 1}) == canonical_id({"a": 1, "b": 2})
    sealed = seal_object({"schema": "x", "value": [1, 2]}, id_field="object_id")
    verify_object(sealed, id_field="object_id")
    with pytest.raises(CBSContractError, match="CBS_CANONICAL_ID_MISMATCH"):
        verify_object({**sealed, "value": [2, 1]}, id_field="object_id")
    with pytest.raises(CBSContractError, match="CBS_NON_FINITE"):
        canonical_id({"bad": float("nan")})


def test_non_transitivity_is_complete() -> None:
    assert len(NON_TRANSITIVITY) == 9
    assert "BENCHMARK_PASS_NE_C2E_ACTIVATION" in NON_TRANSITIVITY


def test_comparator_registry_has_core_diversity_and_no_substitution() -> None:
    registry = load(REGISTRY / "CBS_COMPARATOR_REGISTRY_v0_1.json")
    validate_comparator_registry(registry)
    by_id = {item["id"]: item for item in registry["comparators"]}
    assert registry["minimum_core"] == ["B0", "B1", "B2", "B3", "B9"]
    assert by_id["B3"]["causal_admissibility"] is False
    assert all(by_id[key]["availability"] == "CONDITIONAL_NOT_ADMITTED" for key in ("B4", "B5", "B6", "B7"))
    assert by_id["B8"]["rule"] == "NEVER_FITTED_TARGET_OR_GROUND_TRUTH"


def test_estimands_and_owner_authority_fail_closed() -> None:
    validate_estimand_identity({"estimand":"REFERENCE_BOUNDARY_AUDIT","denominator_id":"u1"}, Estimand.REFERENCE_BOUNDARY_AUDIT)
    with pytest.raises(CBSContractError, match="ESTIMAND_CROSSING"):
        validate_estimand_identity({"estimand":"CONSENSUS_BOUNDARY_DISCOVERY","denominator_id":"u2"}, Estimand.REFERENCE_BOUNDARY_AUDIT)
    with pytest.raises(CBSContractError, match="CBS_OWNER_AUTHORITY_VIOLATION"):
        validate_authority_delta(["C2E_PACK_REPLACE"])


def test_research_generation_is_content_addressed_and_non_authorizing() -> None:
    record = build_research_generation(generation=1, role="SYNTHETIC", predecessor_id=None, exposure_frontier_id="exposure-v1")
    assert record["authority_effect"] == "NONE"
    verify_object(record, id_field="research_generation_id")


def test_schema_registry_reason_codes_and_retention_boundary() -> None:
    schema = load(ROOT / "schemas" / "research_operations" / "cbs" / "cbs_object_minimum_v0_1.schema.json")
    assert "BoundaryEvaluationUniverse" in schema["properties"]["object_type"]["enum"]
    assert schema["$defs"]["boundaryEstimate"]["properties"]["causal_admissibility"]["type"] == "boolean"
    reasons = load(REGISTRY / "CBS_REASON_CODE_REGISTRY_v0_1.json")["codes"]
    assert reasons["ASCERTAINMENT_FAIL"] == "QUARANTINE"
    assert reasons["CAPACITY_EXCEEDED"] == "STOP_PRESERVE_PARTIAL_NO_SCOPE_DRIFT"
    retention = load(REGISTRY / "CBS_ARTIFACT_RETENTION_BOUNDARY_v0_1.json")
    assert set(retention["forbidden_retention"]) == {"WINNER_ONLY", "TOP_N_ONLY", "POSITIVE_ONLY", "SILENT_PRUNING"}


def test_core_contracts_preserve_boundary_and_freeze_rules() -> None:
    contract_root = ROOT / "contracts" / "research_operations" / "cbs"
    core = (contract_root / "CBS_CORE_CONTRACT_v0_1.md").read_text(encoding="utf-8")
    source = (contract_root / "CBS_SOURCE_AND_INPUT_PROJECTION_CONTRACT_v0_1.md").read_text(encoding="utf-8")
    causal = (contract_root / "CBS_CAUSAL_ADMISSIBILITY_AND_FVT_CONTRACT_v0_1.md").read_text(encoding="utf-8")
    freeze = (contract_root / "CBS_PREREGISTRATION_FREEZE_AND_AMENDMENT_POLICY_v0_1.md").read_text(encoding="utf-8")
    assert "benchmark PASS is not C2E activation" in core
    assert "formed before comparator detections" in source
    assert "knowledge cannot be backdated" in causal
    assert "MEANING_BEARING_SUCCESSOR" in freeze


def test_wp1_vit_bindings_are_canonical() -> None:
    wp1 = DOCS / "wp1"
    for name in ("CBSI_WP1_VIT_AUTHORITY_MANIFEST_v0_1.json", "CBSI_WP1_VIT_DEPENDENCY_FRONTIER_v0_1.json"):
        value = load(wp1 / name)
        assert canonical_sha256(value["payload"]) == value["logical_id"]
