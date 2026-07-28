from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery.corr2_evidence import (
    DEFERRED_OBJECTS,
    Corr2EvidenceError,
    build_exact_evidence_context,
    exact_evidence_references,
    validate_exact_evidence_references,
)
from ovc.research_operations.pattern_discovery.pilot_corr2_review_closure import (
    INPUT_SCHEMA,
    Corr2ReviewError,
    build_deferred_review_template,
    validate_corr2_review_input,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = ROOT / "schemas/research_operations/pattern_discovery"


def detail(candidate_id: str) -> dict:
    fingerprint_id = f"PDPILOT-FINGERPRINT-{candidate_id.rsplit('-', 1)[-1]}"
    return {
        "summary": {
            "queue_item_id": f"PDQI-{candidate_id}",
            "candidate_window_id": candidate_id,
            "clock": "15M",
            "price_side": "BID",
            "window_start_utc": "2026-06-22T08:00:00Z",
            "window_end_utc": "2026-06-22T09:00:00Z",
            "trigger_first_valid_at": "2026-06-22T08:15:00Z",
            "primary_trigger_reason": "STRUCTURAL_TRANSITION",
            "quality_state": "GAPPED_SOURCE_ACCEPTED_FOR_PILOT",
            "fingerprint_id": fingerprint_id,
            "nearest_cluster_id": None,
            "nearest_cluster_distance": None,
        },
        "fingerprint": {
            "fingerprint_id": fingerprint_id,
            "fingerprint_version": "PD-FINGERPRINT.v1",
            "candidate_window_id": candidate_id,
            "state_path": ["S1", "S2"],
            "transition_path": ["T1"],
            "interaction_events": ["STRUCTURAL_TRANSITION"],
            "cross_scale_context": {"containment_class": "LOCAL_ONLY"},
        },
        "source_lineage": {
            "release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
            "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
            "c2_record_ids": ["C2S-1", "C2S-2"],
            "fingerprint_id": fingerprint_id,
            "fingerprint_version": "PD-FINGERPRINT.v1",
        },
    }


def source(root: Path) -> dict:
    receipt = root / "pilot-review-receipt-v2.json"
    receipt.write_text("{}\n", encoding="utf-8")
    details = {candidate_id: detail(candidate_id) for candidate_id in DEFERRED_OBJECTS}
    return {
        "review_v2_paths": {"pilot-review-receipt-v2.json": receipt},
        "console_bundle": {"candidate_details": details},
        "queue_rows": [value["summary"] for value in details.values()],
        "fingerprints": [value["fingerprint"] for value in details.values()],
    }


def completed_decision(template: dict, disposition: str) -> dict:
    item = dict(template)
    item["final_disposition"] = disposition
    item["notes"] = "Exact queue, candidate, fingerprint and lineage evidence were inspected."
    if disposition == "WORKFLOW_ACCEPTED":
        item["closure_basis"] = "The exact structural evidence is complete and reviewable."
        item["acceptance_criteria"] = ["All required exact references resolve to this candidate."]
    elif disposition == "REJECT_PILOT_OBJECT":
        item["finding_code"] = "PD-REJECT-CORR2-STRUCTURAL-001"
        item["structural_basis"] = "The object is rejected only for a reproducible structural reviewability condition."
    elif disposition == "DEFER_PILOT_OBJECT":
        item["finding_code"] = "PD-DEFER-CORR2-EVIDENCE-001"
        item["resolution_criteria"] = ["The named exact evidence condition is resolved."]
        item["next_review_condition"] = "Re-review only after the exact evidence condition is present."
    return item


class C1cG5Corr2ReviewClosureTests(unittest.TestCase):
    def test_exact_references_are_candidate_specific_and_fail_closed(self) -> None:
        candidate_id = next(iter(DEFERRED_OBJECTS))
        references = exact_evidence_references(candidate_id)
        self.assertEqual(len(references), 4)
        self.assertTrue(all(candidate_id in item for item in references))
        self.assertEqual(validate_exact_evidence_references(candidate_id, references), sorted(references))
        with self.assertRaisesRegex(Corr2EvidenceError, "REFERENCES_MISSING"):
            validate_exact_evidence_references(candidate_id, references[:-1])
        wrong = list(references)
        wrong[0] = wrong[0].replace(candidate_id, "PDPILOT-CANDIDATE-WRONG")
        with self.assertRaisesRegex(Corr2EvidenceError, "REFERENCES_MISSING"):
            validate_exact_evidence_references(candidate_id, wrong)

    def test_exact_context_binds_queue_fingerprint_and_lineage(self) -> None:
        candidate_id = next(iter(DEFERRED_OBJECTS))
        value = detail(candidate_id)
        context = build_exact_evidence_context(value, queue_item=value["summary"])
        self.assertEqual(context["candidate_window_id"], candidate_id)
        self.assertTrue(context["is_deferred_object"])
        self.assertEqual(context["prior_finding_code"], DEFERRED_OBJECTS[candidate_id])
        self.assertEqual(context["authority"]["canonical_append"], "DENIED")
        bad = dict(value["summary"])
        bad["candidate_window_id"] = "PDPILOT-CANDIDATE-WRONG"
        with self.assertRaisesRegex(Corr2EvidenceError, "QUEUE_DETAIL_IDENTITY_MISMATCH"):
            build_exact_evidence_context(value, queue_item=bad)

    def test_template_contains_exactly_two_deferred_objects_and_no_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            template = build_deferred_review_template(source(Path(temporary)))
        self.assertEqual(template["schema"], INPUT_SCHEMA)
        self.assertEqual({item["candidate_window_id"] for item in template["decisions"]}, set(DEFERRED_OBJECTS))
        self.assertEqual(len(template["decisions"]), 2)
        self.assertFalse(template["second_machine_replay_required"])
        self.assertTrue(template["pilot_only"])
        self.assertEqual(template["canonical_append"], "DENIED")

    def test_complete_accept_and_reject_review_normalizes_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_value = source(Path(temporary))
            template = build_deferred_review_template(source_value)
            review = {
                "schema": INPUT_SCHEMA,
                "packet_id": "C1C-G5-CORR2",
                "gate_id": "C1C-G5-CORRECTIVE-PILOT-REVIEW",
                "pilot_run_id": "PD.PILOT.RUN.96c16f11717e787f971851ee",
                "pilot_namespace": "PD.PILOT.GBPUSD.20260622_20260625.v2",
                "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
                "reviewed_at_utc": "2026-07-28T22:30:00Z",
                "source_structured_review_v2_file_sha256": template["source_structured_review_v2_file_sha256"],
                "decisions": [
                    completed_decision(template["decisions"][0], "WORKFLOW_ACCEPTED"),
                    completed_decision(template["decisions"][1], "REJECT_PILOT_OBJECT"),
                ],
            }
            first = validate_corr2_review_input(review, source=source_value)
            second = validate_corr2_review_input({**review, "decisions": list(reversed(review["decisions"]))}, source=source_value)
        self.assertEqual(first, second)
        self.assertEqual([item["final_disposition"] for item in first], sorted(["WORKFLOW_ACCEPTED", "REJECT_PILOT_OBJECT"], key=lambda disposition: next(item["candidate_window_id"] for item in review["decisions"] if item["final_disposition"] == disposition)))

    def test_third_candidate_and_missing_reference_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_value = source(Path(temporary))
            template = build_deferred_review_template(source_value)
            base = {
                "schema": INPUT_SCHEMA,
                "packet_id": "C1C-G5-CORR2",
                "gate_id": "C1C-G5-CORRECTIVE-PILOT-REVIEW",
                "pilot_run_id": "PD.PILOT.RUN.96c16f11717e787f971851ee",
                "pilot_namespace": "PD.PILOT.GBPUSD.20260622_20260625.v2",
                "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
                "reviewed_at_utc": "2026-07-28T22:30:00Z",
                "source_structured_review_v2_file_sha256": template["source_structured_review_v2_file_sha256"],
            }
            decisions = [completed_decision(item, "WORKFLOW_ACCEPTED") for item in template["decisions"]]
            with self.assertRaisesRegex(Corr2ReviewError, "EXACTLY_TWO"):
                validate_corr2_review_input({**base, "decisions": [*decisions, dict(decisions[0])]}, source=source_value)
            decisions[0]["evidence_references"] = decisions[0]["evidence_references"][:-1]
            with self.assertRaisesRegex(Corr2ReviewError, "REFERENCES_MISSING"):
                validate_corr2_review_input({**base, "decisions": decisions}, source=source_value)

    def test_schemas_are_closed_parseable_and_nonactivating(self) -> None:
        names = (
            "c1c_g5_corr2_deferred_review_input_v0_1.schema.json",
            "c1c_g5_corr2_deferred_review_receipt_v0_1.schema.json",
            "c1c_g5_corr2_closure_ledger_v0_1.schema.json",
            "c1c_g5_corr2_evidence_inventory_v0_1.schema.json",
            "c1c_g5_corrective_pilot_review_final_gate_input_v0_1.schema.json",
        )
        for name in names:
            schema = json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIs(schema["additionalProperties"], False)
            serialized = json.dumps(schema, sort_keys=True).lower()
            self.assertNotIn('"probability": {"type": "number"', serialized)
            self.assertNotIn('"trade_direction"', serialized)


if __name__ == "__main__":
    unittest.main()
