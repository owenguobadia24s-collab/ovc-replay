from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256
from ovc.research_operations.p2cti.demand import build_research_demand
from ovc.research_operations.p2cti.query import ReferenceQueryEngine
from ovc.research_operations.p2cti.relations import build_duplicate_screen, build_relation


BUNDLE_PATH = ROOT / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json"
OUTPUT = ROOT / "fixtures/research_operations/p2cti/P2CTII_WP4_REFERENCE_FIXTURE_v0_1.json"


def _relation_ref(entry: dict) -> dict[str, str]:
    source = entry["source_object_ref"]
    return {
        "owner_programme": source["owner_programme"], "object_id": source["object_id"],
        "semantic_generation": source["semantic_generation"], "content_sha256": source["content_sha256"],
    }


def _source_ref(entry: dict) -> dict:
    return dict(entry["source_object_ref"])


def _owner_evidence(reference: dict, predicate: str, *, object_type: str | None = None) -> dict:
    return {
        "object_type": object_type or reference["object_type"], "predicate": predicate,
        "owner_programme": reference["owner_programme"], "source_ref": reference["source_path"],
        "semantic_generation": reference["semantic_generation"],
        "source_sha256": reference["content_sha256"], "authority_refs": reference["authority_refs"],
        "resolution_state": "RESOLVED",
    }


def rebuild() -> bytes:
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    left, right = bundle["entries"][:2]
    frontier = bundle["generation"]["source_frontier_id"]
    left_ref, right_ref = _relation_ref(left), _relation_ref(right)
    relation_source = {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2", "object_type": "THEORY_RECORD",
        "object_id": "OWNER-REL-DESCENDS-FROM", "semantic_generation": "v0.1",
        "source_path": "fixture://source/ancestry", "content_sha256": "1" * 64,
        "authority_refs": ["P2CTII-G3-PASS"], "scientific_payload_copied": False,
    }
    relation_evidence = {
        **relation_source, "relation_type": "DESCENDS_FROM", "left_generation_ref": left_ref,
        "right_generation_ref": right_ref, "source_frontier_id": frontier,
        "resolution_state": "RESOLVED", "evidence_origin": "OWNER_EXPLICIT",
    }
    ancestry = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=left_ref, right_generation_ref=right_ref,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=frontier,
        evidence_refs=["fixture://owner-explicit-ancestry"],
        source_relation_ref=relation_source, owner_relation_evidence=[relation_evidence],
        current_generation_bundle=bundle,
    )
    near = build_relation(
        relation_type="NEAR_DUPLICATE_OF", left_generation_ref=left_ref, right_generation_ref=right_ref,
        qualification="PROPOSED_MACHINE_ASSISTED", source_frontier_id=frontier,
        evidence_refs=["fixture://machine-retrieval"],
    )
    screen = build_duplicate_screen(
        subject_refs=[left_ref, right_ref], source_frontier_id=frontier,
        method_class="LLM_RETRIEVAL", machine_signal="ADVISORY_NEIGHBOUR_ONLY",
    )
    question = {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2", "object_type": "RESEARCH_PROTOCOL",
        "object_id": "RQ-P2CTII-WP4-FIXTURE", "semantic_generation": "v0.1",
        "source_path": "fixture://question/method", "content_sha256": "2" * 64,
        "authority_refs": ["P2CTII-G3-PASS"], "scientific_payload_copied": False,
    }
    rccr = {
        "owner_programme": "RCCR", "object_type": "RCCR_ASSESSMENT",
        "object_id": "RCCR-P2CTII-WP4-FIXTURE", "semantic_generation": "v0.1",
        "source_path": "fixture://rccr/assessment", "content_sha256": "3" * 64,
        "authority_refs": ["RCCR-GATE"], "scientific_payload_copied": False,
    }
    method = build_research_demand(
        source_ref=_source_ref(left), research_question_ref=question, demand_class="METHOD_GAP",
        source_frontier_id=frontier, classification_owner="RCCR", rccr_assessment_ref=rccr,
        source_owner_evidence=[_owner_evidence(_source_ref(left), "THEORY_IDENTITY", object_type="THEORY_RECORD")],
        question_owner_evidence=[_owner_evidence(question, "THEORY_BINDING")],
        rccr_owner_evidence=[_owner_evidence(rccr, "GAP_CLASS")], research_question_status="CURRENT",
    )
    architecture_question = {
        **question, "object_id": "RQ-P2CTII-WP4-ARCHITECTURE",
        "source_path": "fixture://question/architecture", "content_sha256": "4" * 64,
    }
    architecture = build_research_demand(
        source_ref=_source_ref(right), research_question_ref=architecture_question,
        demand_class="ARCHITECTURE_NEED_HYPOTHESIS", source_frontier_id=frontier,
        classification_owner="RCCR", rccr_assessment_ref=rccr,
        source_owner_evidence=[_owner_evidence(_source_ref(right), "THEORY_IDENTITY", object_type="THEORY_RECORD")],
        question_owner_evidence=[_owner_evidence(architecture_question, "THEORY_BINDING")],
        rccr_owner_evidence=[_owner_evidence(rccr, "GAP_CLASS")], research_question_status="CURRENT",
    )
    relation_ids = [
        ancestry["payload"]["relation_id"], near["payload"]["relation_id"], screen["payload"]["screen_id"]
    ]
    visibility = {
        "schema": "ovc-p2cti-query-visibility-context/v0.1", "consumer_class": "WP4_FIXTURE",
        "visibility_state": "REFERENCE_ONLY", "source_frontier_id": frontier,
        "allowed_query_families": [
            "ARCHITECTURE_NEED", "CROSS_MODE", "CURRENT_STATE", "DUPLICATE_SCREEN", "GET_THEORY",
            "HISTORY", "NEXT_THEORY_WORK", "OPEN_DEMAND", "PORTFOLIO_STATE", "RELATIONS", "SEARCH",
            "UNBLOCK_PATH", "WHY_BLOCKED", "WHY_HERE",
        ],
        "visible_subject_ids": sorted(entry["subject_id"] for entry in bundle["entries"]),
        "visible_relation_ids": sorted(relation_ids),
        "visible_demand_ids": sorted([method["payload"]["demand_id"], architecture["payload"]["demand_id"]]),
        "allow_history": True, "allow_aggregate_counts": True,
        "resolution_state": "RESOLVED", "authority_effect": "NONE",
    }
    exposure = {
        "object_type": "DMRP_EXPOSURE", "predicate": "PATH1_PATH2_EXPOSURE",
        "owner_programme": "DMRP", "source_ref": "fixture://dmrp/exposure",
        "semantic_generation": "v0.1", "source_sha256": "e" * 64,
        "authority_refs": ["DMRP-EXPOSURE-BOUNDARY"], "resolution_state": "RESOLVED",
    }
    engine = ReferenceQueryEngine(
        generation_bundle=bundle, relations=[ancestry, near], duplicate_screens=[screen],
        demands=[method, architecture], visibility_context=visibility,
        exposure_owner_evidence=[exposure],
    )
    eligibility = {
        method["payload"]["demand_id"]: {"eligible": True, "reason_codes": ["METHOD_ROUTE_AVAILABLE"]},
        architecture["payload"]["demand_id"]: {"eligible": True, "reason_codes": ["RCCR_ASSESSMENT_BOUND"]},
    }
    subject = left["subject_id"]
    query_calls = {
        "SEARCH": {"text": subject}, "GET_THEORY": {"subject_id": subject},
        "WHY_HERE": {"subject_id": subject}, "CURRENT_STATE": {"subject_id": subject},
        "HISTORY": {}, "RELATIONS": {"subject_id": subject},
        "DUPLICATE_SCREEN": {"subject_id": subject}, "OPEN_DEMAND": {},
        "WHY_BLOCKED": {"demand_id": architecture["payload"]["demand_id"], "reason_codes": []},
        "UNBLOCK_PATH": {"demand_id": architecture["payload"]["demand_id"], "required_evidence_refs": []},
        "NEXT_THEORY_WORK": {"eligibility": eligibility, "authority_refs": ["P2CTII-WP4-AUTO"]},
        "ARCHITECTURE_NEED": {}, "CROSS_MODE": {}, "PORTFOLIO_STATE": {},
    }
    outputs = {family: engine.query(family, **params) for family, params in sorted(query_calls.items())}
    body = {
        "schema": "ovc-p2ctii-wp4-reference-fixture/v0.1",
        "generation_id": bundle["generation"]["generation_id"],
        "source_frontier_id": frontier,
        "relations": [ancestry, near], "duplicate_screens": [screen],
        "research_demands": [method, architecture], "query_outputs": outputs,
        "operational_current_pointer_published": False,
        "semantic_promotion": False, "authority_effect": "NONE",
    }
    return canonical_json_bytes({**body, "content_sha256": canonical_sha256(body)})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rebuilt = rebuild()
    if args.emit:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(rebuilt)
    if args.check and (not OUTPUT.exists() or OUTPUT.read_bytes() != rebuilt):
        raise SystemExit("WP4 reference fixture rebuild mismatch")
    print(json.loads(rebuilt)["content_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
