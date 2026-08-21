from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256
from ovc.research_operations.p1cdi.reference import (
    assemble_evidence_reference,
    assign_series_generation,
    build_correspondence_plane_evidence,
    replay_as_of,
    stage_correspondence,
)


FIXTURE_PATH = ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json"


def identity_bundle(result: dict) -> dict:
    return {key: result[key] for key in ("series", "generation", "projection")}


def rebuild() -> bytes:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    first = assign_series_generation(
        owner_semantic_binding=fixture["owner_semantic_binding"],
        identity_fields=fixture["identity_a"],
        source_first_valid_time=fixture["first_valid_time"],
    )
    rediscovered = assign_series_generation(
        owner_semantic_binding=fixture["owner_semantic_binding"],
        identity_fields=fixture["identity_a"],
        source_first_valid_time=fixture["first_valid_time"],
        existing=[{key: first[key] for key in ("series", "generation", "projection")}],
    )
    successor = assign_series_generation(
        owner_semantic_binding=fixture["owner_semantic_binding"],
        identity_fields=fixture["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[{key: first[key] for key in ("series", "generation", "projection")}],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:successor",
    )

    def plane_evidence(planes: dict, left: str, right: str) -> list[dict]:
        return [
            build_correspondence_plane_evidence(
                owner=fixture["owner_semantic_binding"],
                plane=plane,
                value=planes[plane],
                left_generation_id=left,
                right_generation_id=right,
                source_ref=f"fixture:source:relation:{plane}",
                source_generation="fixture:source:generation:1",
                evidence_first_valid_time="2026-02-01T00:00:00Z",
            )
            for plane in ("core_relation", "occurrence_relation", "envelope_relation", "lineage_relation")
        ]

    exact = stage_correspondence(
        left_projection=first["projection"],
        right_projection=rediscovered["projection"],
        left_generation_record=first["generation"],
        right_generation_record=rediscovered["generation"],
        planes=fixture["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=plane_evidence(
            fixture["exact_planes"], first["projection"]["generation_id"], rediscovered["projection"]["generation_id"]
        ),
        independence_evidence=[{
            "record_id": "fixture:dmrp:unknown",
            "owner": "DMRP_EXPOSURE_INFLUENCE_RECORDS",
            "left_generation_id": first["projection"]["generation_id"],
            "right_generation_id": rediscovered["projection"]["generation_id"],
            "source_ref": "fixture:dmrp:exposure:unknown",
            "source_generation": "fixture:dmrp:generation:1",
            "source_sha256": "c" * 64,
            "current_source_ref": "fixture:dmrp:exposure:unknown",
            "current_source_generation": "fixture:dmrp:generation:1",
            "current_source_sha256": "c" * 64,
            "evidence_first_valid_time": "2026-02-01T00:00:00Z",
            "currentness_state": "CURRENT",
            "independence_state": "INDEPENDENCE_UNKNOWN",
            "authority_effect": "NONE",
        }],
        left_identity_history=[identity_bundle(first)],
        right_identity_history=[identity_bundle(first)],
    )
    successor_identity_history = [
        {key: first[key] for key in ("series", "generation", "projection")},
        {key: successor[key] for key in ("series", "generation", "projection")},
    ]
    non_exact = stage_correspondence(
        left_projection=first["projection"],
        right_projection=successor["projection"],
        left_generation_record=first["generation"],
        right_generation_record=successor["generation"],
        planes=fixture["non_exact_planes"],
        admission_basis="SOURCE_EXPLICIT_DETERMINISTIC_RELATION",
        source_relation_ref="fixture:source:successor",
        plane_evidence_records=plane_evidence(
            fixture["non_exact_planes"], first["projection"]["generation_id"], successor["projection"]["generation_id"]
        ),
        independence_evidence=[{
            "record_id": "fixture:dmrp:dependent",
            "owner": "DMRP_EXPOSURE_INFLUENCE_RECORDS",
            "left_generation_id": first["projection"]["generation_id"],
            "right_generation_id": successor["projection"]["generation_id"],
            "source_ref": "fixture:dmrp:exposure:1",
            "source_generation": "fixture:dmrp:generation:1",
            "source_sha256": "d" * 64,
            "current_source_ref": "fixture:dmrp:exposure:1",
            "current_source_generation": "fixture:dmrp:generation:1",
            "current_source_sha256": "d" * 64,
            "evidence_first_valid_time": "2026-02-01T00:00:00Z",
            "currentness_state": "CURRENT",
            "independence_state": "AFFIRMATIVELY_DEPENDENT",
            "authority_effect": "NONE",
        }],
        left_identity_history=successor_identity_history,
        right_identity_history=successor_identity_history,
    )
    evidence = assemble_evidence_reference(
        generation_id="fixture:generation:1",
        vector_inputs=fixture["vector_inputs"],
        replication_records=fixture["replications"],
        null_records=fixture["null_bindings"],
        contradiction_records=fixture["contradictions"],
        frontier_first_valid_time="2026-02-01T00:00:00Z",
    )
    result = {
        "schema": "p1cdii-wp4-reference-reproduction/v0.1",
        "identity": {"first": first, "rediscovered": rediscovered, "successor": successor},
        "correspondence": {"exact": exact, "non_exact": non_exact},
        "evidence": evidence,
        "history": {
            "initial": replay_as_of(records=fixture["history"], as_of_time="2026-01-15T00:00:00Z"),
            "corrected": replay_as_of(records=fixture["history"], as_of_time="2026-02-15T00:00:00Z"),
        },
        "decision_bearing": False,
        "authority_effect": "NONE",
    }
    return canonical_json_bytes({**result, "content_sha256": canonical_sha256(result)})


if __name__ == "__main__":
    sys.stdout.buffer.write(rebuild())
