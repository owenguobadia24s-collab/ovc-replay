from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ovc.research_operations.pattern_discovery.pilot_discovery import (
    ACCEPTANCE_ID,
    ALLOWED_REVIEW_DISPOSITIONS,
    AUTHORITY_GATE,
    BINDING_ID,
    NEXT_GATE,
    OPERATION_MODE,
    PILOT_BANNER,
    PILOT_NAMESPACE,
    RESEARCH_ROLE,
    RUN_ID,
    SLICE_ID,
    _validate_review,
    load_governed_authority,
    normalise_c2_states,
    run_pilot_from_states,
)
from ovc.research_operations.canonical import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/pattern_discovery/pd_wp1/c2_state_stream.json"


class PdWp5PilotDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.bundle = run_pilot_from_states(cls.rows)

    def test_governed_approval_chain_is_exact(self) -> None:
        authority = load_governed_authority(ROOT)
        gate = authority["gate"]
        self.assertEqual(gate["gate_id"], AUTHORITY_GATE)
        self.assertEqual(gate["gate_status"], "APPROVED")
        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(gate["source_slice_id"], SLICE_ID)
        self.assertEqual(gate["compute_run_id"], RUN_ID)
        self.assertEqual(gate["source_binding_id"], BINDING_ID)
        self.assertEqual(gate["signed_replay_acceptance_id"], ACCEPTANCE_ID)
        self.assertEqual(gate["next_gate"], NEXT_GATE)

    def test_fixture_rehearsal_is_deterministic(self) -> None:
        first = run_pilot_from_states(self.rows)
        second = run_pilot_from_states(list(reversed(self.rows)))
        self.assertEqual(canonical_sha256(first), canonical_sha256(second))
        self.assertGreater(first["counts"]["transitions"], 0)
        self.assertGreater(first["counts"]["trigger_events"], 0)
        self.assertGreater(first["counts"]["candidates"], 0)
        self.assertEqual(first["counts"]["candidates"], first["counts"]["fingerprints"])

    def test_every_derived_object_is_pilot_only_and_non_promotable(self) -> None:
        for collection in (
            self.bundle["transitions"],
            self.bundle["trigger_events"],
            self.bundle["candidates"],
            self.bundle["fingerprints"],
            self.bundle["cluster_versions"],
            self.bundle["console_bundle"]["queue_items"],
        ):
            for record in collection:
                self.assertTrue(record["pilot_only"])
                self.assertEqual(record["promotion_eligibility"], "NON_PROMOTABLE")
                self.assertFalse(record["canonical_discovery_population"])
                self.assertFalse(record["live_prospective"])
                self.assertEqual(record["identity_namespace"], PILOT_NAMESPACE)
        self.assertTrue(all(str(item["window_id"]).startswith("PDPILOT-CANDIDATE-") for item in self.bundle["candidates"]))
        self.assertTrue(all(str(item["fingerprint_id"]).startswith("PDPILOT-FINGERPRINT-") for item in self.bundle["fingerprints"]))

    def test_authority_boundary_remains_closed(self) -> None:
        authority = self.bundle["authority"]
        self.assertTrue(authority["pilot_only"])
        self.assertEqual(authority["canonical_append"], "DENIED")
        self.assertEqual(authority["live_prospective_relabelling"], "DENIED")
        self.assertEqual(authority["semantic_promotion"], "DENIED")
        self.assertEqual(authority["family_promotion"], "DENIED")
        self.assertEqual(authority["active_novelty_ranking"], "DENIED")
        self.assertEqual(authority["selector_mutation"], "DENIED")
        self.assertEqual(authority["release_mutation"], "DENIED")
        self.assertEqual(authority["r2_publication"], "DENIED")
        self.assertEqual(authority["validation_consumption"], "DENIED")
        for field in (
            "probability_authority",
            "risk_authority",
            "exposure_authority",
            "trading_authority",
            "execution_authority",
            "agent_write_authority",
        ):
            self.assertEqual(authority[field], "NONE")

    def test_console_projection_has_persistent_pilot_boundary(self) -> None:
        pilot = self.bundle["console_bundle"]["pilot"]
        self.assertEqual(pilot["banner"], PILOT_BANNER)
        self.assertEqual(pilot["research_role"], RESEARCH_ROLE)
        self.assertEqual(pilot["operation_mode"], OPERATION_MODE)
        self.assertEqual(pilot["coverage_state"], "GAPPED")
        for detail in self.bundle["console_bundle"]["candidate_details"].values():
            self.assertEqual(detail["authority_banner"], PILOT_BANNER)

    def test_review_template_requires_every_promoted_candidate(self) -> None:
        template = self.bundle["review_template"]
        run_id = "PD.PILOT.RUN.TEST"
        template = {**template, "pilot_run_id": run_id}
        review = {
            "schema": "ovc-pd-wp5-pilot-review-input/v1",
            "pilot_run_id": run_id,
            "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "reviewed_at_utc": "2026-07-28T12:00:00Z",
            "decisions": [
                {
                    "candidate_window_id": item["candidate_window_id"],
                    "review_disposition": "WORKFLOW_ACCEPTED",
                    "notes": "fixture review",
                    "ui_friction_codes": [],
                }
                for item in template["decisions"]
            ],
        }
        decisions = _validate_review(review, template, run_id)
        self.assertEqual(len(decisions), len(template["decisions"]))
        self.assertTrue(all(item["review_disposition"] in ALLOWED_REVIEW_DISPOSITIONS for item in decisions))
        self.assertTrue(all(item["pilot_only"] for item in decisions))

    def test_normalisation_is_order_independent_and_exactly_bound(self) -> None:
        first = normalise_c2_states(self.rows)
        second = normalise_c2_states(list(reversed(self.rows)))
        self.assertEqual(first, second)
        self.assertTrue(all(item["c2_release_id"] == "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1" for item in first))
        self.assertTrue(all(item["selector_id"] == "OPT-B.C2.GBPUSD.DISCOVERY.ACTIVE" for item in first))


if __name__ == "__main__":
    unittest.main()
