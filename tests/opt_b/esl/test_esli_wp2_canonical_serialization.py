from __future__ import annotations

import hashlib
import inspect
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ovc.opt_b.esl.canonical import (
    CanonicalizationError,
    canonical_json_v1_bytes,
    canonical_json_v1_text,
    evidence_frontier_logical_hash,
    occurrence_logical_hash,
    occurrence_record_id,
)
from ovc.opt_b.esl.canonical_reference import reference_canonical_json_v1_bytes

ROOT = Path(__file__).resolve().parents[3]
WP2 = ROOT / "fixtures" / "opt_b" / "esl" / "wp2"


def _traces():
    return json.loads((WP2 / "normative_traces.json").read_text(encoding="utf-8"))["traces"]


def test_five_normative_traces_are_byte_identical_across_independent_implementations():
    traces = _traces()
    assert [trace["trace_id"] for trace in traces] == ["G1", "G2", "G3", "G4", "G5"]
    for trace in traces:
        production = canonical_json_v1_bytes(trace["payload"])
        reference = reference_canonical_json_v1_bytes(trace["payload"])
        assert production == reference == trace["canonical_utf8"].encode("utf-8")
        assert hashlib.sha256(production).hexdigest() == trace["sha256"]


def test_ratified_g1_occurrence_identity_is_exact():
    trace = _traces()[0]
    expected_hash = "db177687a9bff538d4dfc0fb96506af230fa50d7ba6fdf99c327e7f0d4c487a4"
    assert occurrence_logical_hash(trace["payload"]) == expected_hash
    assert occurrence_record_id(trace["payload"]) == "so1:" + expected_hash
    assert trace["occurrence_record_id"] == "so1:" + expected_hash


def test_object_key_order_whitespace_unicode_and_number_normalization():
    payload = {"z": Decimal("1.2300"), "a": 1.0, "µ": "Ω", "null": None, "empty": []}
    assert canonical_json_v1_text(payload) == '{"a":1,"empty":[],"null":null,"z":1.23,"µ":"Ω"}'


@pytest.mark.parametrize("value", [-0.0, Decimal("-0"), float("nan"), float("inf"), float("-inf")])
def test_nonfinite_and_negative_zero_fail_closed(value):
    with pytest.raises(CanonicalizationError):
        canonical_json_v1_bytes({"x": value})


def test_null_empty_and_omission_have_distinct_identity():
    payloads = [{"x": None}, {"x": []}, {"x": {}}, {}]
    encoded = [canonical_json_v1_bytes(item) for item in payloads]
    assert len(set(encoded)) == 4
    assert len({hashlib.sha256(item).hexdigest() for item in encoded}) == 4


def test_schema_declared_arrays_are_deterministically_ordered():
    one = {"facets": [{"dimension": "INTERACTION"}, {"dimension": "LOCATION"}, {"dimension": "ORGANISATION"}, {"dimension": "MOTION"}], "source_generation_ids": ["g2", "g1"]}
    two = {"source_generation_ids": ["g1", "g2"], "facets": [{"dimension": "LOCATION"}, {"dimension": "MOTION"}, {"dimension": "ORGANISATION"}, {"dimension": "INTERACTION"}]}
    assert canonical_json_v1_bytes(one) == canonical_json_v1_bytes(two)
    assert canonical_json_v1_text(one).startswith('{"facets":[{"dimension":"LOCATION"},{"dimension":"MOTION"},{"dimension":"ORGANISATION"},{"dimension":"INTERACTION"}]')


def test_identity_projection_excludes_only_own_top_level_id_and_hash():
    base = {"evidence_frontier_id": "EF.1", "nested": {"logical_hash": "upstream-owned"}, "value": 3}
    decorated = {**base, "occurrence_record_id": "so1:" + "0" * 64, "logical_hash": "1" * 64}
    assert occurrence_logical_hash(base) == occurrence_logical_hash(decorated)
    changed_ref = {**base, "evidence_frontier_id": "EF.2"}
    assert occurrence_logical_hash(base) != occurrence_logical_hash(changed_ref)


def test_evidence_frontier_uses_same_hash_discipline():
    base = {"evaluation_cutoff": "2026-06-24T14:30:00Z", "required_ref_ids": ["b", "a"], "source_generation_ids": ["g2", "g1"]}
    decorated = {**base, "evidence_frontier_id": "ef1:placeholder", "logical_hash": "placeholder"}
    assert evidence_frontier_logical_hash(base) == evidence_frontier_logical_hash(decorated)
    assert evidence_frontier_logical_hash(base) == hashlib.sha256(canonical_json_v1_bytes({"evaluation_cutoff": "2026-06-24T14:30:00Z", "required_ref_ids": ["a", "b"], "source_generation_ids": ["g1", "g2"]})).hexdigest()


def test_reference_implementation_does_not_import_production_serializer():
    import ovc.opt_b.esl.canonical_reference as reference
    source = inspect.getsource(reference)
    assert "from .canonical" not in source
    assert "import canonical" not in source


def test_adversarial_catalogues_are_complete_and_permanently_routed():
    av = json.loads((WP2 / "AV_CATALOGUE_v0_1.json").read_text(encoding="utf-8"))
    iav = json.loads((WP2 / "IAV_CATALOGUE_v0_1.json").read_text(encoding="utf-8"))
    assert av["mutable"] is False and iav["mutable"] is False
    assert [x["id"] for x in av["fixtures"]] == [f"AV-{i:02d}" for i in range(1, 38)]
    assert [x["id"] for x in iav["fixtures"]] == [f"IAV-{i:02d}" for i in range(1, 13)]
    assert all(x["scenario"] and x["required_result"] and x["target_test"].endswith(".py") for x in av["fixtures"] + iav["fixtures"])
    assert av["fixtures"][-1]["required_result"].startswith("C3 base structural statement remains evaluable")
    assert iav["fixtures"][-1]["required_result"].startswith("Return FULL_RESEARCH_HANDOFF")


def test_serialization_registry_is_frozen_and_matches_contract():
    profile = json.loads((ROOT / "registries" / "opt_b" / "esl" / "CANONICAL_SERIALIZATION_PROFILE_v0_1.json").read_text(encoding="utf-8"))
    assert profile["profile_id"] == "canonical-json-v1"
    assert profile["mutable"] is False
    assert profile["nonfinite_numbers"] == "REJECT"
    assert profile["negative_zero"] == "REJECT"
    assert profile["array_order"]["facets"] == ["LOCATION", "MOTION", "ORGANISATION", "INTERACTION"]
