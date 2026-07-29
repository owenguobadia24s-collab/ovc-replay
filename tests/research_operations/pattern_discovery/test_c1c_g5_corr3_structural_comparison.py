from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.pattern_discovery.clustering import build_partition_cluster_version
from ovc.research_operations.pattern_discovery.corr3_evidence import (
    TARGET_CANDIDATE_ID,
    Corr3EvidenceError,
    build_structural_comparison_context,
    exact_corr3_references,
    validate_exact_corr3_references,
)
from ovc.research_operations.pattern_discovery.pilot_corr3_review_closure import (
    INPUT_SCHEMA,
    Corr3ReviewError,
    build_review_template,
    validate_review_input,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = ROOT / "schemas/research_operations/pattern_discovery"


def fingerprint(candidate_id: str, index: int) -> dict:
    partition = {
        "clock": "15M",
        "price_side": "BID",
        "primary_transition_grammar": "PERSISTENCE",
        "boundary_interaction_class": "BOUNDARY",
        "parent_containment_class": "CONTAINED",
        "closure_class": "MAX_DURATION",
    }
    payload = {
        "record_type": "PatternFingerprint",
        "fingerprint_version": "PD.FINGERPRINT.v0.1",
        "candidate_window_id": candidate_id,
        "source_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
        "source_manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        "window_start_utc": f"2026-06-22T0{index}:00:00Z",
        "window_end_utc": f"2026-06-22T0{index}:15:00Z",
        "scope_id": "SCOPE-1",
        "partition": partition,
        "state_path": {
            "initial": {
                "LOCATION": f"EVALUATED|L{index % 2}|",
                "INTERACTION": "EVALUATED|APPROACHING|",
                "ORGANISATION": "EVALUATED|BALANCED|",
                "MOTION": "EVALUATED|UP_PROGRESS|",
                "QUALITY": "EVALUATED|PASS|",
            },
            "terminal": {
                "LOCATION": f"EVALUATED|L{(index + 1) % 2}|",
                "INTERACTION": "EVALUATED|APPROACHING|",
                "ORGANISATION": "EVALUATED|BALANCED|",
                "MOTION": "EVALUATED|UP_PROGRESS|",
                "QUALITY": "EVALUATED|PASS|",
            },
            "occupancy": {
                axis: {value: 1.0}
                for axis, value in {
                    "LOCATION": f"EVALUATED|L{index % 2}|",
                    "INTERACTION": "EVALUATED|APPROACHING|",
                    "ORGANISATION": "EVALUATED|BALANCED|",
                    "MOTION": "EVALUATED|UP_PROGRESS|",
                    "QUALITY": "EVALUATED|PASS|",
                }.items()
            },
            "persistence_lengths": {axis: [1] for axis in ("LOCATION", "INTERACTION", "ORGANISATION", "MOTION", "QUALITY")},
        },
        "transition_sequence": [f"T{index % 3}"],
        "interaction_events": ["LONG_PERSISTENCE"],
        "cross_scale": {"parent": "ALIGNED" if index < 4 else "CONFLICT"},
        "duration_persistence": {
            "duration_records": 1 + index,
            "transition_count": 1,
            "switch_count": 0,
            "max_persistence": 1 + index,
        },
        "quality": {
            "not_evaluable_fraction": 0.0,
            "conflict_fraction": 0.0,
            "stale_fraction": 0.0,
            "closure_reason": "MAX_DURATION",
            "censored": False,
        },
        "selection": {
            "trigger_event_ids": ["PDTE-PERSISTENCE"],
            "control_class": "NONE",
            "disposition": "UNREVIEWED",
        },
    }
    return {"fingerprint_id": f"PDFP-{canonical_sha256(payload)[:32]}", **payload}


def fixture() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    ids = [TARGET_CANDIDATE_ID, *[f"PDPILOT-CANDIDATE-SYNTHETIC-{index}" for index in range(1, 5)]]
    fingerprints = [fingerprint(candidate_id, index) for index, candidate_id in enumerate(ids)]
    cluster_versions = [build_partition_cluster_version(fingerprints)]
    candidates = []
    for index, candidate_id in enumerate(ids):
        candidates.append({
            "window_id": candidate_id,
            "status": "READY_FOR_REVIEW",
            "instrument": "GBPUSD",
            "price_side": "BID",
            "clock": "15M",
            "scope_id": "SCOPE-1",
            "window_start_utc": f"2026-06-22T0{index}:00:00Z",
            "window_end_utc": f"2026-06-22T0{index}:15:00Z",
            "candidate_dedup_key": f"DEDUP-{index}",
            "trigger_event_ids": ["PDTE-PERSISTENCE"] if candidate_id == TARGET_CANDIDATE_ID else [],
        })
    trigger_events = [{
        "record_type": "TriggerEvent",
        "trigger_event_id": "PDTE-PERSISTENCE",
        "trigger_id": "TR-PER-001",
        "trigger_version": "PD.TRIGGERS.v0.1",
        "first_valid_at": "2026-06-22T00:00:00Z",
        "reason_code": "LONG_PERSISTENCE",
        "source_transition_ids": ["PDT-1"],
        "operation_mode": "TIME_GATED_REPLAY",
        "closure_profile_id": "CP-RETURN-OR-MAX-DURATION",
        "rate_limit_group": "PERSISTENCE",
        "primary": True,
    }]
    return candidates, fingerprints, cluster_versions, trigger_events


def source(root: Path) -> dict:
    candidates, fingerprints, clusters, events = fixture()
    context = build_structural_comparison_context(
        candidates=candidates,
        fingerprints=fingerprints,
        cluster_versions=clusters,
        trigger_events=events,
    )
    receipt = root / "c1c-g5-corr2-review-receipt.json"
    receipt.write_text("{}\n", encoding="utf-8")
    return {
        "corr3_context": context,
        "corr2_paths": {"c1c-g5-corr2-review-receipt.json": receipt},
    }


class C1cG5Corr3StructuralComparisonTests(unittest.TestCase):
    def test_exact_medoid_distance_and_persistence_context_is_deterministic(self) -> None:
        candidates, fingerprints, clusters, events = fixture()
        first = build_structural_comparison_context(
            candidates=candidates,
            fingerprints=fingerprints,
            cluster_versions=clusters,
            trigger_events=events,
        )
        second = build_structural_comparison_context(
            candidates=list(reversed(candidates)),
            fingerprints=list(reversed(fingerprints)),
            cluster_versions=clusters,
            trigger_events=events,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["candidate_window_id"], TARGET_CANDIDATE_ID)
        self.assertEqual(first["comparison_availability"]["status"], "EXACT_ASSIGNED_MEDOID_AVAILABLE")
        self.assertEqual(
            first["distance_comparison"]["recorded_distance"],
            first["distance_comparison"]["recomputed_distance"],
        )
        self.assertEqual(
            first["distance_comparison"]["weighted_component_total"],
            first["distance_comparison"]["recorded_distance"],
        )
        self.assertEqual(first["long_persistence_derivation"]["frozen_threshold_records"], 4)
        self.assertFalse(first["long_persistence_derivation"]["trigger_rule_changed"])
        self.assertEqual(first["authority"]["canonical_append"], "DENIED")

    def test_duplicate_target_and_missing_exact_reference_fail_closed(self) -> None:
        candidates, fingerprints, clusters, events = fixture()
        with self.assertRaisesRegex(Corr3EvidenceError, "DUPLICATE_CANDIDATE_ID"):
            build_structural_comparison_context(
                candidates=[*candidates, dict(candidates[0])],
                fingerprints=fingerprints,
                cluster_versions=clusters,
                trigger_events=events,
            )
        references = exact_corr3_references()
        self.assertEqual(validate_exact_corr3_references(references), sorted(references))
        with self.assertRaisesRegex(Corr3EvidenceError, "EXACT_REFERENCES_MISSING"):
            validate_exact_corr3_references(references[:-1])

    def test_template_and_completed_review_are_exactly_one_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_value = source(Path(temporary))
            template = build_review_template(source_value)
            self.assertEqual(template["schema"], INPUT_SCHEMA)
            self.assertEqual(template["decision"]["candidate_window_id"], TARGET_CANDIDATE_ID)
            self.assertFalse(template["second_machine_replay_required"])
            decision = dict(template["decision"])
            decision.update({
                "final_disposition": "WORKFLOW_ACCEPTED",
                "notes": "The exact medoid, distance decomposition, overlap status and persistence derivation were reviewed.",
                "closure_basis": "The prior comparison finding is closed by exact read-only preserved-artifact evidence.",
                "acceptance_criteria": ["Assigned medoid and component sum reproduce the recorded distance."],
            })
            review = {
                "schema": INPUT_SCHEMA,
                "packet_id": "C1C-G5-CORR3",
                "gate_id": "C1C-G5-CORRECTIVE-PILOT-REVIEW",
                "pilot_run_id": "PD.PILOT.RUN.96c16f11717e787f971851ee",
                "pilot_namespace": "PD.PILOT.GBPUSD.20260622_20260625.v2",
                "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
                "reviewed_at_utc": "2026-07-29T02:00:00Z",
                "source_corr2_review_receipt_file_sha256": template["source_corr2_review_receipt_file_sha256"],
                "decision": decision,
            }
            normalized = validate_review_input(review, source=source_value)
            self.assertEqual(normalized["candidate_window_id"], TARGET_CANDIDATE_ID)
            self.assertEqual(normalized["final_disposition"], "WORKFLOW_ACCEPTED")
            wrong = json.loads(json.dumps(review))
            wrong["decision"]["candidate_window_id"] = "PDPILOT-CANDIDATE-UNAUTHORISED"
            with self.assertRaisesRegex(Corr3ReviewError, "UNAUTHORISED_CANDIDATE"):
                validate_review_input(wrong, source=source_value)

    def test_corr3_schemas_are_closed_parseable_and_nonactivating(self) -> None:
        names = (
            "c1c_g5_corr3_review_input_v0_1.schema.json",
            "c1c_g5_corr3_review_receipt_v0_1.schema.json",
            "c1c_g5_corr3_closure_ledger_v0_1.schema.json",
            "c1c_g5_corr3_evidence_inventory_v0_1.schema.json",
            "c1c_g5_corrective_pilot_review_final_gate_input_v0_2.schema.json",
        )
        for name in names:
            schema = json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIs(schema["additionalProperties"], False)
            serialized = json.dumps(schema, sort_keys=True).lower()
            self.assertNotIn('"trade_direction"', serialized)
            self.assertNotIn('"probability": {"type": "number"', serialized)


if __name__ == "__main__":
    unittest.main()
