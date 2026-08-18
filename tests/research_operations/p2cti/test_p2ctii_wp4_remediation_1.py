from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.p2cti.demand import DemandValidationError, build_research_demand
from ovc.research_operations.p2cti.query import QUERY_FAMILIES, QueryValidationError, ReferenceQueryEngine
from ovc.research_operations.p2cti.relations import (
    RelationValidationError,
    build_relation,
    preserve_relation_ambiguity,
    preserve_relation_conflict,
)


ROOT = Path(__file__).resolve().parents[3]
BUNDLE = json.loads(
    (ROOT / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json").read_text(encoding="utf-8")
)
FRONTIER = BUNDLE["generation"]["source_frontier_id"]


def _ref(index: int) -> dict[str, str]:
    source = BUNDLE["entries"][index]["source_object_ref"]
    return {key: source[key] for key in ("owner_programme", "object_id", "semantic_generation", "content_sha256")}


def _owner_ref(*, object_type: str = "THEORY_RECORD", owner: str = "RESEARCH_OPERATIONS_DMRP_PATH2") -> dict:
    return {
        "owner_programme": owner, "object_type": object_type, "object_id": "OWNER-REL-1",
        "semantic_generation": "v0.1", "source_path": "owner://wp4/relation/1",
        "content_sha256": "a" * 64, "authority_refs": ["P2CTII-G3-PASS"],
        "scientific_payload_copied": False,
    }


def _relation_evidence(
    relation_type: str, left: dict, right: dict, *, owner: str = "RESEARCH_OPERATIONS_DMRP_PATH2",
    origin: str = "OWNER_EXPLICIT", state: str = "RESOLVED",
) -> tuple[dict, dict]:
    source = _owner_ref(owner=owner)
    evidence = {
        **source, "relation_type": relation_type, "left_generation_ref": left,
        "right_generation_ref": right, "source_frontier_id": FRONTIER,
        "resolution_state": state, "evidence_origin": origin,
    }
    return source, evidence


def _admitted_relation(relation_type: str = "DESCENDS_FROM") -> dict:
    left, right = _ref(0), _ref(1)
    source, evidence = _relation_evidence(relation_type, left, right)
    return build_relation(
        relation_type=relation_type, left_generation_ref=left, right_generation_ref=right,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=["owner://evidence/1"], source_relation_ref=source,
        owner_relation_evidence=[evidence], current_generation_bundle=BUNDLE,
    )


def _source(index: int = 0) -> dict:
    return deepcopy(BUNDLE["entries"][index]["source_object_ref"])


def _question(index: int = 0) -> dict:
    return {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2", "object_type": "RESEARCH_PROTOCOL",
        "object_id": f"RQ-REM-{index}", "semantic_generation": "v0.1",
        "source_path": f"owner://question/{index}", "content_sha256": f"{index + 2:x}" * 64,
        "authority_refs": ["P2CTII-G3-PASS"], "scientific_payload_copied": False,
    }


def _evidence(reference: dict, predicate: str, *, object_type: str | None = None, state: str = "RESOLVED") -> dict:
    return {
        "object_type": object_type or reference["object_type"], "predicate": predicate,
        "owner_programme": reference["owner_programme"], "source_ref": reference["source_path"],
        "semantic_generation": reference["semantic_generation"], "source_sha256": reference["content_sha256"],
        "authority_refs": reference["authority_refs"], "resolution_state": state,
    }


def _visibility(*records: dict, subjects: list[str] | None = None, allowed: list[str] | None = None) -> dict:
    relation_ids, demand_ids = [], []
    for record in records:
        payload = record.get("payload", {})
        relation_ids.extend(payload[key] for key in ("relation_id", "ambiguity_id", "conflict_id", "screen_id") if key in payload)
        if "demand_id" in payload:
            demand_ids.append(payload["demand_id"])
    return {
        "schema": "ovc-p2cti-query-visibility-context/v0.1", "consumer_class": "WP4_REMEDIATION_TEST",
        "visibility_state": "REFERENCE_ONLY" if subjects is None else "RESTRICTED",
        "source_frontier_id": FRONTIER, "allowed_query_families": sorted(allowed or QUERY_FAMILIES),
        "visible_subject_ids": sorted(subjects if subjects is not None else [row["subject_id"] for row in BUNDLE["entries"]]),
        "visible_relation_ids": sorted(relation_ids), "visible_demand_ids": sorted(demand_ids),
        "allow_history": subjects is None, "allow_aggregate_counts": subjects is None,
        "resolution_state": "RESOLVED", "authority_effect": "NONE",
    }


def test_owner_generation_and_source_admission_fail_closed() -> None:
    assert _admitted_relation()["payload"]["admission_disposition"] == "ADMITTED_SOURCE_EXPLICIT"
    invented = deepcopy(_ref(1))
    invented.update(semantic_generation="v999", content_sha256="f" * 64)
    source, evidence = _relation_evidence("DESCENDS_FROM", _ref(0), invented)
    stale = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=_ref(0), right_generation_ref=invented,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=["owner://invented"], source_relation_ref=source,
        owner_relation_evidence=[evidence], current_generation_bundle=BUNDLE,
    )
    assert stale["payload"]["admission_disposition"] == "PROPOSED_REVIEW_REQUIRED"
    assert "STALE_SEMANTIC_GENERATION_REASSESSMENT_REQUIRED" in stale["payload"]["warnings"]
    with pytest.raises(RelationValidationError):
        build_relation(
            relation_type="DESCENDS_FROM", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
            qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
            evidence_refs=[], source_relation_ref="opaque-owner-text",
        )


def test_missing_duplicate_wrong_and_machine_owner_evidence_cannot_auto_admit() -> None:
    left, right = _ref(0), _ref(1)
    source, evidence = _relation_evidence("DESCENDS_FROM", left, right)
    missing = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=left, right_generation_ref=right,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=[], source_relation_ref=source, current_generation_bundle=BUNDLE,
    )
    assert missing["payload"]["admission_disposition"] != "ADMITTED_SOURCE_EXPLICIT"
    duplicate = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=left, right_generation_ref=right,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=[], source_relation_ref=source, owner_relation_evidence=[evidence, evidence],
        current_generation_bundle=BUNDLE,
    )
    assert duplicate["payload"]["admission_disposition"] == "CONFLICT_PRESERVED"
    wrong_source, wrong = _relation_evidence("DESCENDS_FROM", left, right, owner="RCCR")
    wrong_record = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=left, right_generation_ref=right,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=[], source_relation_ref=wrong_source, owner_relation_evidence=[wrong],
        current_generation_bundle=BUNDLE,
    )
    assert wrong_record["payload"]["admission_disposition"] == "CONFLICT_PRESERVED"
    _, machine = _relation_evidence("DESCENDS_FROM", left, right, origin="MACHINE_ASSISTED")
    with pytest.raises(RelationValidationError):
        build_relation(
            relation_type="DESCENDS_FROM", left_generation_ref=left, right_generation_ref=right,
            qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
            evidence_refs=[], source_relation_ref=source, owner_relation_evidence=[machine],
            current_generation_bundle=BUNDLE,
        )


def test_relation_order_permutation_is_deterministic() -> None:
    kwargs = {
        "relation_type": "DESCENDS_FROM", "left_generation_ref": _ref(0), "right_generation_ref": _ref(1),
        "qualification": "SOURCE_EXPLICIT_DETERMINISTIC", "source_frontier_id": FRONTIER,
        "current_generation_bundle": BUNDLE,
    }
    source, evidence = _relation_evidence("DESCENDS_FROM", _ref(0), _ref(1))
    first = build_relation(**kwargs, source_relation_ref=source, owner_relation_evidence=[evidence], evidence_refs=["b", "a"])
    second = build_relation(**kwargs, source_relation_ref=source, owner_relation_evidence=[evidence], evidence_refs=["a", "b"])
    assert first == second


def test_research_question_owner_currentness_and_status_are_exact() -> None:
    source, question = _source(), _question()
    kwargs = {
        "source_ref": source, "research_question_ref": question, "demand_class": "REPLICATION_NEED",
        "source_frontier_id": FRONTIER,
        "source_owner_evidence": [_evidence(source, "THEORY_IDENTITY", object_type="THEORY_RECORD")],
        "question_owner_evidence": [_evidence(question, "THEORY_BINDING")],
    }
    assert build_research_demand(**kwargs, research_question_status="CURRENT")["payload"]["research_question_status"] == "CURRENT"
    for status in ("SUPERSEDED", "STALE", "UNRESOLVED"):
        with pytest.raises(DemandValidationError):
            build_research_demand(**kwargs, research_question_status=status)
    stale = deepcopy(kwargs)
    stale["question_owner_evidence"] = [_evidence(question, "THEORY_BINDING", state="UNRESOLVED")]
    with pytest.raises(DemandValidationError):
        build_research_demand(**stale, research_question_status="CURRENT")


def test_query_bundle_currentness_frontier_and_history_coherence() -> None:
    with pytest.raises(QueryValidationError):
        ReferenceQueryEngine(generation_bundle={"schema": BUNDLE["schema"]}, visibility_context=_visibility())
    stale = deepcopy(BUNDLE)
    stale["currentness_evaluation"]["source_frontier_id"] = "p2cti:frontier:" + "0" * 64
    with pytest.raises(QueryValidationError):
        ReferenceQueryEngine(generation_bundle=stale, visibility_context=_visibility())
    history = [{"generation_id": BUNDLE["generation"]["generation_id"], "generation_ordinal": 1}]
    with pytest.raises(QueryValidationError):
        ReferenceQueryEngine(generation_bundle=BUNDLE, visibility_context=_visibility(), historical_generations=history)


def test_query_surfaces_ambiguity_and_conflict_without_silent_loss() -> None:
    first, second = _admitted_relation("DESCENDS_FROM"), _admitted_relation("COMPETES_WITH")
    ambiguity = preserve_relation_ambiguity(
        subject_refs=[_ref(0), _ref(1)],
        competing_relation_refs=[first["payload"]["relation_id"], second["payload"]["relation_id"]],
        source_frontier_id=FRONTIER,
    )
    conflict = preserve_relation_conflict(
        subject_refs=[_ref(0), _ref(1)],
        accepted_relation_refs=[first["payload"]["relation_id"], second["payload"]["relation_id"]],
        source_frontier_id=FRONTIER,
    )
    records = [first, second, ambiguity, conflict]
    engine = ReferenceQueryEngine(generation_bundle=BUNDLE, relations=records, visibility_context=_visibility(*records))
    result = engine.query("RELATIONS", subject_id=_ref(0)["object_id"])
    assert len(result["result"]["ambiguities"]) == 1
    assert len(result["result"]["conflicts"]) == 1
    assert result["ambiguity_state"] == "UNRESOLVED"
    assert result["conflict_state"] == "BLOCKING"


def test_visibility_firewall_and_cross_mode_exposure_fail_closed() -> None:
    cross_mode = build_relation(
        relation_type="CROSS_MODE_RELATED", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="PROPOSED_MACHINE_ASSISTED", source_frontier_id=FRONTIER, evidence_refs=["machine://1"],
    )
    hidden = ReferenceQueryEngine(
        generation_bundle=BUNDLE, relations=[cross_mode],
        visibility_context=_visibility(cross_mode, subjects=[]),
    )
    assert hidden.query("GET_THEORY", subject_id=_ref(0)["object_id"])["result"] is None
    search = hidden.query("SEARCH", text="TH-", limit=1)
    assert search["result"] == {"matches": [], "truncation": None}
    cross = hidden.query("CROSS_MODE")
    assert cross["result"] == []
    assert "CROSS_MODE_EXPOSURE_UNRESOLVED" in cross["warnings"]


def test_query_results_are_detached_from_engine_state() -> None:
    engine = ReferenceQueryEngine(generation_bundle=BUNDLE, visibility_context=_visibility())
    subject = _ref(0)["object_id"]
    first = engine.query("GET_THEORY", subject_id=subject)
    first["result"]["inventory_entry"]["subject_id"] = "MUTATED"
    assert engine.query("GET_THEORY", subject_id=subject)["result"]["inventory_entry"]["subject_id"] == subject


def test_all_14_query_families_remain_coherent_under_empty_visible_state() -> None:
    engine = ReferenceQueryEngine(generation_bundle=BUNDLE, visibility_context=_visibility())
    subject = _ref(0)["object_id"]
    calls = {
        "SEARCH": {"text": "not-present"}, "GET_THEORY": {"subject_id": subject},
        "WHY_HERE": {"subject_id": subject}, "CURRENT_STATE": {"subject_id": subject}, "HISTORY": {},
        "RELATIONS": {"subject_id": subject}, "DUPLICATE_SCREEN": {"subject_id": subject},
        "OPEN_DEMAND": {}, "WHY_BLOCKED": {"demand_id": "missing"},
        "UNBLOCK_PATH": {"demand_id": "missing"},
        "NEXT_THEORY_WORK": {"eligibility": {}, "authority_refs": ["WP4"]},
        "ARCHITECTURE_NEED": {}, "CROSS_MODE": {}, "PORTFOLIO_STATE": {},
    }
    assert set(calls) == QUERY_FAMILIES
    for family, params in calls.items():
        envelope = engine.query(family, **params)
        assert envelope["authority_effect"] == "NONE"
        assert envelope["decision_bearing"] is False


def test_remediation_logical_evidence_is_byte_equal_in_two_clean_processes() -> None:
    command = [sys.executable, str(ROOT / "scripts/research_operations/run_p2ctii_wp4_remediation_1.py")]
    first = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "73"}, check=True, capture_output=True).stdout
    second = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": "1907"}, check=True, capture_output=True).stdout
    assert first == second
