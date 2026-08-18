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
    replay_as_of,
    stage_correspondence,
)


FIXTURE_PATH = ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json"


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
    exact = stage_correspondence(
        left_projection=first["projection"],
        right_projection=rediscovered["projection"],
        planes=fixture["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
    )
    non_exact = stage_correspondence(
        left_projection=first["projection"],
        right_projection=successor["projection"],
        planes=fixture["non_exact_planes"],
        admission_basis="SOURCE_EXPLICIT_DETERMINISTIC_RELATION",
        source_relation_ref="fixture:source:successor",
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
