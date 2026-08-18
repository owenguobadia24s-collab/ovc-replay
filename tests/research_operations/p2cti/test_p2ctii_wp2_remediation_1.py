from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.p2cti.currentness import (
    OPTIONAL_CURRENTNESS_OWNERS,
    REQUIRED_CURRENTNESS_OWNERS,
    build_source_frontier,
    evaluate_two_point_currentness,
)
from ovc.research_operations.p2cti.identity import generation_id, series_id


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = (
    ROOT
    / "fixtures/research_operations/p2cti/P2CTII_WP2_OWNER_CURRENTNESS_FIXTURES_v0_1.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
BLOCK_REVIEW = (
    ROOT
    / "docs/programmes/p2cti-v0-1/wp2/P2CTII_G2_ALG_CONSOLIDATED_REVIEW_PACKET_v0_1.json"
)
BLOCK_REVIEW_SHA256 = "d44e1d45e291e3db0932df2b8103b6e3d74941174747013d38f8716da077ba47"


def _frontier(rows: list[dict], *, unresolved: tuple[str, ...] = ()) -> dict:
    return build_source_frontier(copy.deepcopy(rows), unresolved_reasons=unresolved)


def _identity(frontier_id: str) -> tuple[str, str]:
    series = series_id()
    generation = generation_id(
        series=series,
        generation_ordinal=0,
        member_entry_ids=["p2cti:entry:" + "a" * 64],
        source_frontier=frontier_id,
    )
    return series, generation


def _evaluate(before: dict, after: dict) -> dict:
    usable_frontier_id = before.get("frontier_id")
    if not isinstance(usable_frontier_id, str):
        usable_frontier_id = _frontier(FIXTURE["frontier_before"])["frontier_id"]
    series, generation = _identity(usable_frontier_id)
    return evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=after,
    )


def _optional_binding() -> dict:
    return {
        "owner_programme": "DMRP",
        "source_ref": "records/research_operations/dmrp/candidate-generation-001.json",
        "source_sha256": "4" * 64,
        "semantic_generation": "1",
        "authority_refs": ["authority:dmrp"],
        "required": False,
    }


def _rehash(frontier: dict) -> dict:
    changed = copy.deepcopy(frontier)
    body = {name: value for name, value in changed.items() if name != "content_sha256"}
    changed["content_sha256"] = canonical_sha256(body)
    return changed


def test_immutable_g2_alg_block_review_is_byte_identical() -> None:
    assert hashlib.sha256(BLOCK_REVIEW.read_bytes()).hexdigest() == BLOCK_REVIEW_SHA256
    review = json.loads(BLOCK_REVIEW.read_text(encoding="utf-8"))
    assert review["gate_decision"] == "BLOCK"
    assert review["authority_delta"] == "NONE"
    assert [item["id"] for item in review["discrepancies"]] == [
        "P2CTII_G2_ALG_BLOCK_001_REQUIRED_OWNER_COMPLETENESS_NOT_BOUND",
        "P2CTII_G2_ALG_BLOCK_002_RUNTIME_FRONTIER_SCHEMA_ENFORCEMENT_GAP",
    ]


def test_required_owner_contract_is_registry_bound_not_caller_supplied() -> None:
    assert REQUIRED_CURRENTNESS_OWNERS == ("RCCR", "RESEARCH_OPERATIONS_DMRP_PATH2")
    assert OPTIONAL_CURRENTNESS_OWNERS == ("DMRP", "EC1")
    registry = json.loads(
        (
            ROOT
            / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json"
        ).read_text(encoding="utf-8")
    )
    contract = registry["source_frontier_contract"]
    assert contract["required_owner_programmes"] == list(REQUIRED_CURRENTNESS_OWNERS)
    assert contract["optional_owner_programmes"] == list(OPTIONAL_CURRENTNESS_OWNERS)
    assert contract["historical_fallback"] == "FORBIDDEN"


def test_block_001_exactly_one_required_owner_omitted_never_complete_or_current() -> None:
    rows = [
        row
        for row in FIXTURE["frontier_before"]
        if row["owner_programme"] != "RCCR"
    ]
    frontier = _frontier(rows)
    assert frontier["missing_required_owners"] == ["RCCR"]
    assert frontier["unresolved_reasons"] == ["OWNER_SOURCE_MISSING:RCCR"]
    assert frontier["completeness_state"] == "UNRESOLVED"
    result = _evaluate(frontier, copy.deepcopy(frontier))
    assert result["currentness_state"] == "UNRESOLVED"
    assert result["frontiers_equal"] is True
    assert result["decision_bearing"] is False


def test_multiple_required_owners_omitted_and_optional_owner_omitted() -> None:
    optional_only = _frontier([_optional_binding()])
    assert optional_only["missing_required_owners"] == [
        "RCCR",
        "RESEARCH_OPERATIONS_DMRP_PATH2",
    ]
    assert optional_only["completeness_state"] == "UNRESOLVED"
    assert _evaluate(optional_only, optional_only)["currentness_state"] == "UNRESOLVED"

    required_only = _frontier(FIXTURE["frontier_before"])
    assert required_only["missing_required_owners"] == []
    assert required_only["completeness_state"] == "COMPLETE"
    assert _evaluate(required_only, required_only)["currentness_state"] == "CURRENT"


def test_all_required_owners_present_with_optional_owner_is_complete() -> None:
    frontier = _frontier([*FIXTURE["frontier_before"], _optional_binding()])
    assert frontier["required_owner_programmes"] == list(REQUIRED_CURRENTNESS_OWNERS)
    assert frontier["missing_required_owners"] == []
    assert frontier["conflicting_owner_programmes"] == []
    assert frontier["completeness_state"] == "COMPLETE"
    assert _evaluate(frontier, frontier)["currentness_state"] == "CURRENT"


def test_duplicate_or_conflicting_owner_records_fail_closed_with_typed_evidence() -> None:
    exact_duplicate = [*FIXTURE["frontier_before"], copy.deepcopy(FIXTURE["frontier_before"][0])]
    with pytest.raises(ValueError, match="duplicate owner/source"):
        _frontier(exact_duplicate)

    conflicting = copy.deepcopy(FIXTURE["frontier_before"])
    second_path2 = copy.deepcopy(conflicting[0])
    second_path2["source_ref"] = "records/research_operations/path2/theory-002.json"
    second_path2["source_sha256"] = "5" * 64
    frontier = _frontier([*conflicting, second_path2])
    assert frontier["conflicting_owner_programmes"] == ["RESEARCH_OPERATIONS_DMRP_PATH2"]
    assert frontier["completeness_state"] == "INCOMPLETE_BLOCKING"
    assert "STATE_OWNER_CONFLICT:RESEARCH_OPERATIONS_DMRP_PATH2" in frontier["unresolved_reasons"]
    assert _evaluate(frontier, frontier)["currentness_state"] == "UNRESOLVED"


def test_invalid_owner_identifier_type_and_required_flag_are_rejected() -> None:
    unknown = copy.deepcopy(FIXTURE["frontier_before"])
    unknown[0]["owner_programme"] = "UNREGISTERED_OWNER"
    with pytest.raises(ValueError, match="unknown owner_programme"):
        _frontier(unknown)

    malformed_type = copy.deepcopy(FIXTURE["frontier_before"])
    malformed_type[0]["owner_programme"] = 7
    with pytest.raises(ValueError, match="owner_programme must be a non-empty string"):
        _frontier(malformed_type)

    caller_relabels_required = copy.deepcopy(FIXTURE["frontier_before"])
    caller_relabels_required[0]["required"] = False
    with pytest.raises(ValueError, match="required flag conflicts with registry"):
        _frontier(caller_relabels_required)


def test_block_002_schema_invalid_but_two_point_byte_equal_is_typed_unresolved() -> None:
    valid = _frontier(FIXTURE["frontier_before"])
    invalid = copy.deepcopy(valid)
    invalid["unexpected_convenience_field"] = "same-on-both-reads"
    invalid = _rehash(invalid)
    result = _evaluate(invalid, copy.deepcopy(invalid))
    assert result["currentness_state"] == "UNRESOLVED"
    assert result["frontier_validation_state"] == "INVALID"
    assert result["warnings"] == ["CURRENTNESS_UNRESOLVED"]
    assert result["frontiers_equal"] is False
    assert result["advisory_pointer"] is None
    assert result["operational_pointer_switched"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "UNKNOWN_TOP_LEVEL_FIELD",
        "MISSING_REQUIRED_FIELD",
        "INVALID_REQUIRED_FIELD_TYPE",
        "STRUCTURALLY_INCOMPLETE_BINDING",
        "WRONG_SCHEMA_CONSTANT",
    ],
)
def test_runtime_exact_schema_enforcement_rejects_malformed_frontiers(mutation: str) -> None:
    invalid = _frontier(FIXTURE["frontier_before"])
    if mutation == "UNKNOWN_TOP_LEVEL_FIELD":
        invalid["observed_at"] = "2099-01-01T00:00:00Z"
    elif mutation == "MISSING_REQUIRED_FIELD":
        del invalid["authority_effect"]
    elif mutation == "INVALID_REQUIRED_FIELD_TYPE":
        invalid["source_bindings"][0]["required"] = 1
    elif mutation == "STRUCTURALLY_INCOMPLETE_BINDING":
        del invalid["source_bindings"][0]["source_ref"]
    elif mutation == "WRONG_SCHEMA_CONSTANT":
        invalid["schema_family"] = "CONVENIENT_FRONTIER"
    invalid = _rehash(invalid)
    result = _evaluate(invalid, invalid)
    assert result["currentness_state"] == "UNRESOLVED"
    assert result["frontier_validation_state"] == "INVALID"
    assert result["warnings"] == ["CURRENTNESS_UNRESOLVED"]
    assert result["advisory_pointer"] is None


def test_valid_complete_equal_and_advancing_frontiers_remain_distinct() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    equal = _frontier(list(reversed(FIXTURE["frontier_before"])))
    current = _evaluate(before, equal)
    assert current["currentness_state"] == "CURRENT"
    assert current["frontiers_equal"] is True
    assert current["advisory_pointer"] is not None
    assert current["advisory_pointer"]["decision_bearing"] is False

    advanced = _frontier(FIXTURE["frontier_generation_advanced"])
    moved = _evaluate(before, advanced)
    assert moved["currentness_state"] == "SOURCE_GENERATION_ADVANCED"
    assert moved["frontiers_equal"] is False
    assert moved["historical_generation_disposition"] == "RETAINED_ADDRESSABLE"
    assert moved["historical_fallback"] == "FORBIDDEN"


def test_invalid_or_incomplete_historical_generation_cannot_fallback() -> None:
    current = _frontier(FIXTURE["frontier_before"])
    incomplete = _frontier([FIXTURE["frontier_before"][0]])
    unresolved = _evaluate(current, incomplete)
    assert unresolved["currentness_state"] == "UNRESOLVED"
    assert unresolved["historical_generation_disposition"] == "RETAINED_ADDRESSABLE"
    assert unresolved["historical_fallback"] == "FORBIDDEN"

    invalid = copy.deepcopy(incomplete)
    invalid["source_bindings"][0]["source_sha256"] = "not-a-hash"
    invalid = _rehash(invalid)
    rejected = _evaluate(current, invalid)
    assert rejected["currentness_state"] == "UNRESOLVED"
    assert rejected["historical_fallback"] == "FORBIDDEN"
    assert rejected["advisory_pointer"] is None


def test_convenience_fields_cannot_change_or_manufacture_semantic_identity() -> None:
    valid = _frontier(FIXTURE["frontier_before"])
    first = copy.deepcopy(valid)
    second = copy.deepcopy(valid)
    first["path_title"] = "Newest"
    second["path_title"] = "Oldest"
    first = _rehash(first)
    second = _rehash(second)
    result = _evaluate(first, second)
    assert result["currentness_state"] == "UNRESOLVED"
    assert result["frontier_validation_state"] == "INVALID"
    assert result["warnings"] == ["CURRENTNESS_UNRESOLVED"]
    assert result["advisory_pointer"] is None


def test_source_order_permutation_is_deterministic_in_two_clean_processes() -> None:
    script = r"""
import hashlib
import json
from pathlib import Path
from ovc.research_operations.p2cti.currentness import build_source_frontier, evaluate_two_point_currentness
from ovc.research_operations.p2cti.identity import generation_id, series_id
root = Path.cwd()
fixture = json.loads((root / "fixtures/research_operations/p2cti/P2CTII_WP2_OWNER_CURRENTNESS_FIXTURES_v0_1.json").read_text())
before = build_source_frontier(fixture["frontier_before"])
after = build_source_frontier(list(reversed(fixture["frontier_before"])))
series = series_id()
generation = generation_id(series=series, generation_ordinal=0, member_entry_ids=["p2cti:entry:" + "a" * 64], source_frontier=before["frontier_id"])
result = evaluate_two_point_currentness(series_id=series, generation_id=generation, prebuild_frontier=before, prepublish_frontier=after)
payload = json.dumps({"before": before, "after": after, "result": result}, sort_keys=True, separators=(",", ":")).encode()
print(hashlib.sha256(payload).hexdigest())
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    outputs = [
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for _ in range(2)
    ]
    assert outputs[0] == outputs[1]
    assert len(outputs[0]) == 64
