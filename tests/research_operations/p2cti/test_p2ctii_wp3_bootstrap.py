from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from ovc.research_operations.canonical import canonical_json_bytes
from ovc.research_operations.p2cti.bootstrap import BootstrapValidationError, build_generation_zero
from ovc.research_operations.p2cti.currentness import build_source_frontier, evaluate_two_point_currentness


ROOT = Path(__file__).resolve().parents[3]
CENSUS_PATH = ROOT / "registries/research_operations/p2cti/P2CTII_BOOTSTRAP_SOURCE_CENSUS_v0_1.json"
RECEIPT_PATH = ROOT / "fixtures/research_operations/p2cti/P2CTII_WP3_SOURCE_REPRODUCTION_v0_1.json"
RCCR_PATH = ROOT / "registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json"
OUTPUT_PATH = ROOT / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/research_operations/p2cti/p2cti_inventory_v0_1.schema.json"


def _schema_valid(value: object, schema: dict, root: dict) -> bool:
    if "$ref" in schema:
        target: object = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]  # type: ignore[index]
        return _schema_valid(value, target, root)  # type: ignore[arg-type]
    if "oneOf" in schema:
        return sum(_schema_valid(value, branch, root) for branch in schema["oneOf"]) == 1
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    expected_type = schema.get("type")
    allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
    type_match = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "boolean": type(value) is bool,
        "null": value is None,
        None: True,
    }
    if not any(type_match.get(name, False) for name in allowed_types):
        return False
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return False
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            return False
    if type(value) is int and value < schema.get("minimum", value):
        return False
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            return False
        return all(_schema_valid(item, schema.get("items", {}), root) for item in value)
    if isinstance(value, dict):
        if not set(schema.get("required", ())).issubset(value):
            return False
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and not set(value).issubset(properties):
            return False
        return all(
            key not in properties or _schema_valid(item, properties[key], root)
            for key, item in value.items()
        )
    return True


def _inputs() -> tuple[dict, dict, bytes, dict]:
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    raw = RCCR_PATH.read_bytes()
    pointer = json.loads(raw)
    return census, receipt, raw, pointer


def _build(*, census: dict | None = None, receipt: dict | None = None, status: str = "PASS") -> dict:
    source_census, source_receipt, raw, pointer = _inputs()
    return build_generation_zero(
        census=census or source_census,
        source_reproduction=receipt or source_receipt,
        rccr_pointer_ref=RCCR_PATH.relative_to(ROOT).as_posix(),
        rccr_pointer_sha256=hashlib.sha256(raw).hexdigest(),
        rccr_semantic_generation=pointer["current_state"],
        g2_alg_status=status,
    )


def test_exact_lossless_30_entry_bootstrap_and_schema() -> None:
    bundle = _build()
    entries = bundle["entries"]
    assert len(entries) == 30
    assert len({entry["subject_id"] for entry in entries}) == 30
    assert sum(entry["subject_class"] == "EXTERNAL_THEORY_RECORD" for entry in entries) == 7
    assert sum(entry["subject_class"] == "IN_HOUSE_THEORY_RECORD" for entry in entries) == 19
    assert sum(entry["subject_class"] == "ARCHITECTURE_NEED_SEED" for entry in entries) == 4
    assert all(entry["source_object_ref"]["scientific_payload_copied"] is False for entry in entries)
    assert all(entry["source_object_ref"]["object_type"] == entry["subject_class"] for entry in entries)
    assert bundle["generation"]["completeness_state"] == "COMPLETE"
    assert bundle["currentness_evaluation"]["currentness_state"] == "CURRENT"
    assert bundle["currentness_evaluation"]["decision_bearing"] is False
    assert bundle["operational_current_pointer_published"] is False
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    for value in [bundle["series"], bundle["generation"], bundle["generation_manifest"], *entries]:
        assert _schema_valid(value, schema, schema)


def test_exact_canonical_materialisation_matches_clean_rebuild() -> None:
    assert OUTPUT_PATH.read_bytes() == canonical_json_bytes(_build())


@pytest.mark.parametrize("mutation", ["bytes_not_reproduced", "missing_subject", "wrong_hash", "wrong_locator"])
def test_g3_fails_closed_without_exact_source_reproduction(mutation: str) -> None:
    census, receipt, _, _ = _inputs()
    damaged = deepcopy(receipt)
    document = damaged["documents"][0]
    if mutation == "bytes_not_reproduced":
        document["exact_bytes_reproduced"] = False
    elif mutation == "missing_subject":
        document["reproduced_subject_ids"].pop()
    elif mutation == "wrong_hash":
        document["sha256"] = "0" * 64
    else:
        document["drive_file_id"] = "convenient-but-not-bound"
    with pytest.raises(BootstrapValidationError):
        _build(census=census, receipt=damaged)


def test_omission_duplication_and_seed_coercion_fail_closed() -> None:
    census, receipt, _, _ = _inputs()
    omitted = deepcopy(census)
    omitted["members"].pop()
    duplicate = deepcopy(census)
    duplicate["members"][-1]["subject_id"] = duplicate["members"][-2]["subject_id"]
    coerced = deepcopy(census)
    coerced["members"][-1]["subject_class"] = "IN_HOUSE_THEORY_RECORD"
    for damaged in (omitted, duplicate, coerced):
        with pytest.raises(BootstrapValidationError):
            _build(census=damaged, receipt=receipt)


def test_g2_pass_is_required_and_grants_no_new_authority() -> None:
    with pytest.raises(BootstrapValidationError):
        _build(status="BLOCK")
    bundle = _build()
    assert bundle["authority_effect"] == "NONE"
    assert all(entry["authority_effect"] == "NONE" for entry in bundle["entries"])


def test_duplicate_screen_is_exact_and_non_semantic() -> None:
    screen = _build()["duplicate_screen"]
    assert screen["screened_subject_count"] == 30
    assert screen["duplicate_groups"] == []
    assert screen["basis"] == "EXACT_SUBJECT_ID_AND_SOURCE_OBJECT_REF"
    assert screen["semantic_inference_performed"] is False


def test_current_and_historical_dual_proof_retains_old_generation() -> None:
    bundle = _build()
    before = bundle["source_frontier"]
    bindings = deepcopy(before["source_bindings"])
    path2 = next(row for row in bindings if row["owner_programme"] == "RESEARCH_OPERATIONS_DMRP_PATH2")
    path2["semantic_generation"] = "P2CTII-WP3-SYNTHETIC-SOURCE-ADVANCE"
    path2["source_sha256"] = "1" * 64
    after = build_source_frontier(bindings)
    evaluation = evaluate_two_point_currentness(
        series_id=bundle["series"]["series_id"],
        generation_id=bundle["generation"]["generation_id"],
        prebuild_frontier=before, prepublish_frontier=after,
    )
    assert evaluation["currentness_state"] == "SOURCE_GENERATION_ADVANCED"
    assert evaluation["historical_generation_disposition"] == "RETAINED_ADDRESSABLE"
    assert evaluation["historical_fallback"] == "FORBIDDEN"
    assert json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))["generation"]["generation_id"] == bundle["generation"]["generation_id"]


def test_two_clean_processes_are_byte_identical() -> None:
    command = [sys.executable, str(ROOT / "scripts/research_operations/run_p2ctii_wp3_bootstrap.py")]
    env = {**os.environ, "PYTHONHASHSEED": "random"}
    first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, env=env).stdout
    second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, env=env).stdout
    assert first == second
    assert first.decode().strip() == _build()["content_sha256"]


def test_source_order_permutation_does_not_change_semantic_generation() -> None:
    census, receipt, _, _ = _inputs()
    permuted = deepcopy(receipt)
    permuted["documents"].reverse()
    assert _build(census=census, receipt=permuted) == _build(census=census, receipt=receipt)
