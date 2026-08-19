from __future__ import annotations

from copy import deepcopy
from itertools import permutations
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.p2cti.demand import DemandValidationError, build_research_demand
from ovc.research_operations.p2cti.query import QUERY_FAMILIES, ReferenceQueryEngine
from ovc.research_operations.p2cti.relations import RelationValidationError, build_relation


ROOT = Path(__file__).resolve().parents[3]
BUNDLE = json.loads(
    (ROOT / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json")
    .read_text(encoding="utf-8")
)
FRONTIER = BUNDLE["generation"]["source_frontier_id"]


def _ref(index: int) -> dict[str, str]:
    source = BUNDLE["entries"][index]["source_object_ref"]
    return {
        key: source[key]
        for key in ("owner_programme", "object_id", "semantic_generation", "content_sha256")
    }


def _source(index: int = 0) -> dict:
    return deepcopy(BUNDLE["entries"][index]["source_object_ref"])


def _owner_source(
    relation_type: str = "DESCENDS_FROM",
    *,
    owner: str = "RESEARCH_OPERATIONS_DMRP_PATH2",
    source_path: str | None = None,
    generation: str = "v0.1",
    suffix: str = "a",
) -> dict:
    return {
        "owner_programme": owner,
        "object_type": "THEORY_RECORD",
        "object_id": f"OWNER-{relation_type}-{suffix}",
        "semantic_generation": generation,
        "source_path": source_path or f"owner://relation/{relation_type}/{suffix}",
        "content_sha256": suffix * 64,
        "authority_refs": ["P2CTII-G3-PASS"],
        "scientific_payload_copied": False,
    }


def _relation_evidence(
    source: dict,
    relation_type: str = "DESCENDS_FROM",
    *,
    left: dict | None = None,
    right: dict | None = None,
    frontier: str = FRONTIER,
    state: str = "RESOLVED",
    origin: str = "OWNER_EXPLICIT",
) -> dict:
    return {
        **deepcopy(source),
        "relation_type": relation_type,
        "left_generation_ref": deepcopy(left or _ref(0)),
        "right_generation_ref": deepcopy(right or _ref(1)),
        "source_frontier_id": frontier,
        "resolution_state": state,
        "evidence_origin": origin,
    }


def _relation(
    relation_type: str = "DESCENDS_FROM",
    *,
    right: dict | None = None,
    qualification: str = "SOURCE_EXPLICIT_DETERMINISTIC",
    evidence: list[dict] | None = None,
    source: dict | None = None,
) -> dict:
    source = source or _owner_source(relation_type)
    rows = evidence if evidence is not None else [
        _relation_evidence(source, relation_type, right=right)
    ]
    return build_relation(
        relation_type=relation_type,
        left_generation_ref=_ref(0),
        right_generation_ref=right or _ref(1),
        qualification=qualification,
        source_frontier_id=FRONTIER,
        evidence_refs=["owner://evidence"],
        source_relation_ref=source,
        owner_relation_evidence=rows,
        current_generation_bundle=BUNDLE,
    )


def _owner_predicate_evidence(reference: dict, predicate: str, *, state: str = "RESOLVED") -> dict:
    return {
        "object_type": reference["object_type"],
        "predicate": predicate,
        "owner_programme": reference["owner_programme"],
        "source_ref": reference["source_path"],
        "semantic_generation": reference["semantic_generation"],
        "source_sha256": reference["content_sha256"],
        "authority_refs": deepcopy(reference["authority_refs"]),
        "resolution_state": state,
    }


def _question(generation: str = "v0.1") -> dict:
    return {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2",
        "object_type": "RESEARCH_PROTOCOL",
        "object_id": "RQ-WP4-REMEDIATION-2",
        "semantic_generation": generation,
        "source_path": "owner://question/wp4-remediation-2",
        "content_sha256": ("2" if generation == "v0.1" else "9") * 64,
        "authority_refs": ["P2CTII-G3-PASS"],
        "scientific_payload_copied": False,
    }


def _demand(question: dict | None = None, frontier: str = FRONTIER) -> dict:
    source = _source()
    question = question or _question()
    return build_research_demand(
        source_ref=source,
        research_question_ref=question,
        demand_class="REPLICATION_NEED",
        source_frontier_id=frontier,
        source_owner_evidence=[
            {
                **_owner_predicate_evidence(source, "THEORY_IDENTITY"),
                "object_type": "THEORY_RECORD",
            }
        ],
        question_owner_evidence=[_owner_predicate_evidence(question, "THEORY_BINDING")],
        research_question_status="CURRENT",
    )


def _record_id(record: dict) -> str:
    payload = record["payload"]
    return next(
        payload[name]
        for name in ("relation_id", "screen_id", "ambiguity_id", "conflict_id")
        if name in payload
    )


def _visibility(records: list[dict] | tuple[dict, ...] = ()) -> dict:
    return {
        "schema": "ovc-p2cti-query-visibility-context/v0.1",
        "consumer_class": "WP4_REMEDIATION_2_TEST",
        "visibility_state": "REFERENCE_ONLY",
        "source_frontier_id": FRONTIER,
        "allowed_query_families": sorted(QUERY_FAMILIES),
        "visible_subject_ids": sorted(entry["subject_id"] for entry in BUNDLE["entries"]),
        "visible_relation_ids": sorted({_record_id(record) for record in records}),
        "visible_demand_ids": [],
        "allow_history": True,
        "allow_aggregate_counts": True,
        "resolution_state": "RESOLVED",
        "authority_effect": "NONE",
    }


def _exposure(generation: str = "v0.1", state: str = "RESOLVED", suffix: str = "e") -> dict:
    return {
        "object_type": "DMRP_EXPOSURE",
        "predicate": "PATH1_PATH2_EXPOSURE",
        "owner_programme": "DMRP",
        "source_ref": f"dmrp://exposure/{suffix}",
        "semantic_generation": generation,
        "source_sha256": suffix * 64,
        "authority_refs": ["DMRP-EXPOSURE"],
        "resolution_state": state,
    }


def _raises(exc_type: type[Exception], fn) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def build_remediation_2_evidence() -> dict:
    disguised_source = _owner_source(source_path="machine://generated/disguised", suffix="b")
    disguised = _relation(
        source=disguised_source,
        evidence=[_relation_evidence(disguised_source)],
    )

    source_a = _owner_source(suffix="a")
    source_b = _owner_source(generation="v0.2", suffix="b")
    source_c = _owner_source(owner="RCCR", suffix="c")
    evidence_a = _relation_evidence(source_a)
    evidence_b = _relation_evidence(source_b)
    evidence_c = _relation_evidence(source_c)
    conflict_outputs = [
        _relation(source=source_a, evidence=list(order))
        for order in permutations((evidence_a, evidence_b, evidence_c))
    ]
    conflict_hashes = {canonical_sha256(value) for value in conflict_outputs}

    duplicate = _relation(source=source_a, evidence=[evidence_a, deepcopy(evidence_a)])
    machine = _relation_evidence(source_a, origin="MACHINE_ASSISTED")
    mixed_rejected = _raises(
        RelationValidationError,
        lambda: _relation(source=source_a, evidence=[evidence_a, machine]),
    )
    stale = _relation_evidence(
        source_b, frontier="p2cti:frontier:" + "0" * 64
    )
    stale_current = [
        _relation(source=source_a, evidence=list(order))
        for order in permutations((evidence_a, stale))
    ]

    stale_question = _question("v0.0")
    stale_question_rejected = _raises(DemandValidationError, lambda: _demand(stale_question))
    stale_frontier_rejected = _raises(
        DemandValidationError,
        lambda: _demand(frontier="p2cti:frontier:" + "0" * 64),
    )

    invented = deepcopy(_ref(1))
    invented.update(semantic_generation="v999", content_sha256="f" * 64)
    stale_relation = _relation(right=invented)
    unresolved_source = _owner_source(suffix="d")
    unresolved_relation = _relation(source=unresolved_source, evidence=[])
    admitted = _relation()
    relation_outputs = [
        ReferenceQueryEngine(
            generation_bundle=BUNDLE,
            relations=list(order),
            visibility_context=_visibility([admitted, stale_relation, unresolved_relation]),
        ).query("RELATIONS", subject_id=_ref(0)["object_id"])
        for order in permutations((admitted, stale_relation, unresolved_relation))
    ]
    relation_hashes = {canonical_sha256(value) for value in relation_outputs}
    degraded = relation_outputs[0]

    similarity = build_relation(
        relation_type="CROSS_MODE_RELATED",
        left_generation_ref=_ref(0),
        right_generation_ref=_ref(1),
        qualification="PROPOSED_MACHINE_ASSISTED",
        source_frontier_id=FRONTIER,
        evidence_refs=["similarity://only"],
        current_generation_bundle=BUNDLE,
    )
    wrong_cross = build_relation(
        relation_type="CROSS_MODE_RELATED",
        left_generation_ref=_ref(0),
        right_generation_ref=invented,
        qualification="PROPOSED_MACHINE_ASSISTED",
        source_frontier_id=FRONTIER,
        evidence_refs=["similarity://wrong-generation"],
        current_generation_bundle=BUNDLE,
    )
    formal_source = _owner_source("CROSS_MODE_RELATED", suffix="e")
    formal = _relation(
        "CROSS_MODE_RELATED",
        source=formal_source,
        evidence=[_relation_evidence(formal_source, "CROSS_MODE_RELATED")],
        qualification="INDEPENDENT_RULE_REVIEWED",
    )

    def cross(record: dict, exposure: list[dict]) -> dict:
        return ReferenceQueryEngine(
            generation_bundle=BUNDLE,
            relations=[record],
            visibility_context=_visibility([record]),
            exposure_owner_evidence=exposure,
        ).query("CROSS_MODE")

    stale_exposure = cross(formal, [_exposure("v0.0", suffix="a")])
    missing_exposure = cross(formal, [])
    similarity_output = cross(similarity, [_exposure()])
    wrong_cross_output = cross(wrong_cross, [_exposure()])
    formal_output = cross(formal, [_exposure()])

    cases = {
        "MACHINE_GENERATED_PROVENANCE_DISGUISED_AS_OWNER_EVIDENCE": disguised["payload"]["admission_disposition"] != "ADMITTED_SOURCE_EXPLICIT",
        "SOURCE_ORDER_PERMUTATIONS": len(conflict_hashes) == 1,
        "STALE_RESEARCH_QUESTION_GENERATION": stale_question_rejected,
        "CURRENT_QUESTION_WITH_STALE_SOURCE_FRONTIER": stale_frontier_rejected,
        "CURRENT_WITH_ONE_STALE_CONSTITUENT": degraded["currentness_state"] != "CURRENT",
        "COMPLETE_WITH_UNRESOLVED_CONSTITUENT": degraded["completeness_state"] != "COMPLETE",
        "WARNING_OMISSION": {
            "RELATION_CONSTITUENT_NOT_CURRENT",
            "RELATION_OWNER_EVIDENCE_UNRESOLVED",
        }.issubset(degraded["warnings"]),
        "STALE_EXPOSURE_RECORD": stale_exposure["result"] == [],
        "WRONG_CANDIDATE_GENERATION": wrong_cross_output["result"] == [],
        "THEORY_SIMILARITY_NOT_SUBSTITUTED_FOR_FORMAL_CORRESPONDENCE": similarity_output["result"] == [],
        "REORDER_INPUT_COLLECTION": len(relation_hashes) == 1,
        "EXACT_LOOKING_OPAQUE_STRING_REJECTED": _raises(
            RelationValidationError,
            lambda: build_relation(
                relation_type="DESCENDS_FROM",
                left_generation_ref=_ref(0),
                right_generation_ref=_ref(1),
                qualification="SOURCE_EXPLICIT_DETERMINISTIC",
                source_frontier_id=FRONTIER,
                evidence_refs=[],
                source_relation_ref="owner://looks-exact",
                current_generation_bundle=BUNDLE,
            ),
        ),
        "THREE_WAY_CONFLICT_ALL_PERMUTATIONS": len(conflict_hashes) == 1 and all(
            row["payload"]["admission_disposition"] == "CONFLICT_PRESERVED"
            for row in conflict_outputs
        ),
        "DUPLICATE_IDENTICAL_EVIDENCE_FAILS_FROZEN_DUPLICATE_RULE": duplicate["payload"]["admission_disposition"] == "CONFLICT_PRESERVED",
        "MIXED_PROPOSED_AND_AUTHORITATIVE_EVIDENCE_FAILS_CLOSED": mixed_rejected,
        "STALE_AND_CURRENT_EVIDENCE_ORDER_INDEPENDENT": stale_current[0] == stale_current[1],
        "CURRENT_QUESTION_AND_FRONTIER_CONTROL": _demand()["payload"]["research_question_status"] == "CURRENT",
        "QUERY_WARNING_ORDER_CANONICAL": degraded["warnings"] == sorted(set(degraded["warnings"])),
        "NO_EXPOSURE_RECORD_NOT_INDEPENDENT": missing_exposure["result"] == [] and "CROSS_MODE_EXPOSURE_UNRESOLVED" in missing_exposure["warnings"],
        "FORMAL_CURRENT_CROSS_MODE_CONTROL": formal_output["result"] == [formal],
        "PLAUSIBLE_PROVENANCE_NE_OWNER_EVIDENCE": disguised["payload"]["owner_evidence_state"] == "CONFLICT",
        "VALID_HISTORICAL_GENERATION_NE_CURRENT_GENERATION": stale_question_rejected,
        "PAYLOAD_AVAILABLE_NE_QUERY_CURRENT": degraded["result"]["relations"] != [] and degraded["currentness_state"] != "CURRENT",
        "PAYLOAD_AVAILABLE_NE_QUERY_COMPLETE": degraded["result"]["relations"] != [] and degraded["completeness_state"] != "COMPLETE",
        "SIMILARITY_NE_CROSS_MODE_CORRESPONDENCE": similarity_output["result"] == [],
        "INPUT_ORDER_NE_EVIDENCE_PRECEDENCE": len(conflict_hashes) == 1,
    }
    return {
        "schema": "ovc-p2ctii-wp4-remediation-2-evidence/v0.1",
        "case_count": len(cases),
        "cases": {name: "PASS" if passed else "FAIL" for name, passed in sorted(cases.items())},
        "conflict_permutation_count": len(conflict_outputs),
        "query_permutation_count": len(relation_outputs),
        "conflict_output_sha256": next(iter(conflict_hashes)) if len(conflict_hashes) == 1 else None,
        "query_output_sha256": next(iter(relation_hashes)) if len(relation_hashes) == 1 else None,
        "authority_delta": "NONE",
    }


def test_all_eleven_fresh_blockers_and_neighbors_are_permanent_regressions() -> None:
    evidence = build_remediation_2_evidence()
    failures = [name for name, result in evidence["cases"].items() if result != "PASS"]
    assert failures == []
    assert evidence["conflict_permutation_count"] == 6
    assert evidence["query_permutation_count"] == 6


def test_returned_and_caller_objects_remain_detached() -> None:
    first, second = _relation(), _relation("COMPETES_WITH")
    caller = deepcopy(first)
    engine = ReferenceQueryEngine(
        generation_bundle=BUNDLE,
        relations=[caller, second],
        visibility_context=_visibility([caller, second]),
    )
    output = engine.query("RELATIONS", subject_id=_ref(0)["object_id"])
    output["result"]["relations"][0]["payload"]["relation_type"] = "MUTATED"
    caller["payload"]["relation_type"] = "MUTATED"
    reproduced = engine.query("RELATIONS", subject_id=_ref(0)["object_id"])
    assert [row["payload"]["relation_type"] for row in reproduced["result"]["relations"]] == [
        "DESCENDS_FROM",
        "COMPETES_WITH",
    ]


def test_remediation_2_runner_is_byte_equal_in_two_clean_processes() -> None:
    command = [sys.executable, str(ROOT / "scripts/research_operations/run_p2ctii_wp4_remediation_2.py")]
    first = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONHASHSEED": "83"},
        check=True,
        capture_output=True,
    ).stdout
    second = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONHASHSEED": "1901"},
        check=True,
        capture_output=True,
    ).stdout
    assert first == second
    assert len(first.decode().strip()) == 64
