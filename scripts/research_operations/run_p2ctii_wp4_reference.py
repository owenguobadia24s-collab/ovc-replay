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


def _source_ref(entry: dict) -> dict[str, str]:
    source = entry["source_object_ref"]
    return {
        "owner_programme": source["owner_programme"], "object_type": source["object_type"],
        "object_id": source["object_id"], "semantic_generation": source["semantic_generation"],
        "content_sha256": source["content_sha256"],
    }


def rebuild() -> bytes:
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    left, right = bundle["entries"][:2]
    frontier = bundle["generation"]["source_frontier_id"]
    left_ref, right_ref = _relation_ref(left), _relation_ref(right)
    ancestry = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=left_ref, right_generation_ref=right_ref,
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=frontier,
        evidence_refs=["fixture://owner-explicit-ancestry"],
        source_relation_ref="fixture://source/ancestry",
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
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2", "question_id": "RQ-P2CTII-WP4-FIXTURE",
        "semantic_generation": "v0.1", "content_sha256": "2" * 64,
    }
    rccr = {
        "owner_programme": "RCCR", "object_type": "RCCR_ASSESSMENT",
        "object_id": "RCCR-P2CTII-WP4-FIXTURE", "semantic_generation": "v0.1",
        "content_sha256": "3" * 64,
    }
    method = build_research_demand(
        source_ref=_source_ref(left), research_question_ref=question, demand_class="METHOD_GAP",
        source_frontier_id=frontier, classification_owner="RCCR", rccr_assessment_ref=rccr,
    )
    architecture_question = {**question, "question_id": "RQ-P2CTII-WP4-ARCHITECTURE", "content_sha256": "4" * 64}
    architecture = build_research_demand(
        source_ref=_source_ref(right), research_question_ref=architecture_question,
        demand_class="ARCHITECTURE_NEED_HYPOTHESIS", source_frontier_id=frontier,
        classification_owner="RCCR", rccr_assessment_ref=rccr,
    )
    engine = ReferenceQueryEngine(
        generation_bundle=bundle, relations=[ancestry, near], duplicate_screens=[screen],
        demands=[method, architecture],
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
