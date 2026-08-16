from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.dmrp_path2_prereg import (
    Path2PreregValidationError,
    make_path2_prereg_record,
    preregistration_effective,
    verify_path2_prereg_record,
)

ROOT = Path(__file__).resolve().parents[2]


def _fixture() -> dict:
    return json.loads((ROOT / "fixtures/research_operations/p2_ext_prereg/SYNTHETIC_NATIVE_PREREG.json").read_text())


def test_three_native_record_families_round_trip_and_authority_firewall() -> None:
    for kind, record_type in (("theory", "THEORY_RECORD"), ("protocol", "RESEARCH_PROTOCOL"), ("experiment", "EXPERIMENT_RECORD")):
        record = make_path2_prereg_record(record_type, _fixture()["records"][kind])
        verify_path2_prereg_record(json.loads(json.dumps(record)))
        assert record["authority_effect"] == "NONE"
        assert record["schema_family"] == "DMRP_PATH2_PREREG"
        assert record["record_id"].startswith(f"ro:p2:{kind}:")


def test_scientific_identity_is_independent_of_physical_attempt_and_artifact_location() -> None:
    payload = _fixture()["records"]["protocol"]
    a = make_path2_prereg_record("RESEARCH_PROTOCOL", payload, physical_attempt_id="host-a", artifact_refs=({"path":"/tmp/a"},))
    b = make_path2_prereg_record("RESEARCH_PROTOCOL", payload, physical_attempt_id="host-b", artifact_refs=({"path":"/tmp/b"},))
    assert a["semantic_sha256"] == b["semantic_sha256"]
    assert a["record_sha256"] != b["record_sha256"]


def test_effective_preregistration_fails_closed_without_exact_bindings() -> None:
    payload = dict(_fixture()["records"]["experiment"])
    payload["preregistration_state"] = "PREREGISTERED_EFFECTIVE"
    payload["dependency_state"] = "BOUND"
    with pytest.raises(Path2PreregValidationError):
        make_path2_prereg_record("EXPERIMENT_RECORD", payload)


def test_result_artifacts_candidate_formation_and_validation_are_denied() -> None:
    for field, value in (("result_artifacts", ["forbidden-result"]), ("candidate_formation", "EXECUTED"), ("validation", "CONSUMED")):
        payload = dict(_fixture()["records"]["experiment"])
        payload[field] = value
        with pytest.raises(Path2PreregValidationError):
            make_path2_prereg_record("EXPERIMENT_RECORD", payload)


def test_theory_must_remain_untested_and_path1_influence_forbidden() -> None:
    theory = dict(_fixture()["records"]["theory"])
    theory["evidence_state"] = "SUPPORTED"
    with pytest.raises(Path2PreregValidationError):
        make_path2_prereg_record("THEORY_RECORD", theory)
    theory = dict(_fixture()["records"]["theory"])
    theory["path1_influence"] = "SEED"
    with pytest.raises(Path2PreregValidationError):
        make_path2_prereg_record("THEORY_RECORD", theory)


def test_native_registry_exactly_binds_frozen_method_packs_and_partition() -> None:
    native = json.loads((ROOT / "registries/research_operations/P2_EXT_NATIVE_PREREGISTRATION_REGISTRY_v0_1.json").read_text())
    frozen = json.loads((ROOT / "registries/research_operations/P2_EXT_FROZEN_METHOD_PARAMETER_REGISTRY_v0_1.json").read_text())
    partition = json.loads((ROOT / "registries/research_operations/P2_EXT_PARALLEL_ROUTE_PREREG_PARTITION_v0_1.json").read_text())
    native_by_protocol = {p["protocol_id"]: p for p in native["protocols"]}
    frozen_by_protocol = {p["protocol_id"]: p for p in frozen["packs"]}
    assert set(native_by_protocol) == set(frozen_by_protocol) == set(partition["protocols"])
    for protocol_id, item in native_by_protocol.items():
        assert item["method_parameter_pack_id"] == frozen_by_protocol[protocol_id]["pack_id"]
        assert item["method_parameter_sha256"] == frozen_by_protocol[protocol_id]["canonical_sha256"]
        assert item["preregistration_state"] == "NATIVE_BOUND_NOT_EFFECTIVE"
    assert native["effective_preregistration_count"] == 0
    assert native["real_source_execution"] == "DENIED"
    assert native["durable_real_source_append"] == "DENIED"
    assert native_by_protocol["RP-EC1-EXT-0006-v0.1"]["dependency_state"] == "DEPENDENCY_UNAVAILABLE"
    assert native_by_protocol["RP-EC1-EXT-0007-v0.1"]["dependency_state"] == "POPULATION_PENDING"


def test_existing_research_operations_v01_and_dmrp_v02_schemas_are_unchanged_additive_boundaries() -> None:
    v1 = json.loads((ROOT / "schemas/research_operations/research_records_v0_1.schema.json").read_text())
    v2 = json.loads((ROOT / "schemas/research_operations/research_records_v0_2.schema.json").read_text())
    p2 = json.loads((ROOT / "schemas/research_operations/dmrp_path2_prereg_v0_1.schema.json").read_text())
    assert v1["$defs"]["Envelope"]["properties"]["schema_version"]["const"] == "0.1"
    assert v2["$defs"]["Envelope"]["properties"]["schema_version"]["const"] == "0.2"
    assert "THEORY_RECORD" not in v2["$defs"]["Envelope"]["properties"]["record_type"]["enum"]
    assert p2["$defs"]["Envelope"]["properties"]["schema_family"]["const"] == "DMRP_PATH2_PREREG"


def test_current_experiment_records_are_not_effective() -> None:
    payload = _fixture()["records"]["experiment"]
    record = make_path2_prereg_record("EXPERIMENT_RECORD", payload)
    assert not preregistration_effective(record["scientific_payload"])
