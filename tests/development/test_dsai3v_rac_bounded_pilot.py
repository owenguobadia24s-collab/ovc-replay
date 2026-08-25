from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ovc.development.identity import canonical_sha256
from ovc.development.skills.repository_assurance_pilot import (
    PILOT_BASELINE_SCHEMA,
    PILOT_CLASS,
    RepositoryAssurancePilotError,
    build_pilot_certificate,
    classify_candidate,
)
from ovc.development.skills.vit_routing import build_vit_payload_lineage_record

ROOT = Path(__file__).resolve().parents[2]


def _policy(status: str = "ACTIVE_BOUNDED_PILOT") -> dict:
    return {
        "schema": "ovc-rac-delta-assurance-pilot-policy/v1",
        "policy_id": "DSAI3V-RAC-PILOT-POLICY-v0.1",
        "programme_id": "OVC-DSAI3V-CIPR-REPOSITORY-ASSURANCE-CONTINUITY-AMENDMENT-0.1",
        "operator_decision_id": "a" * 64,
        "status": status,
        "pilot_class": PILOT_CLASS,
        "receipt_prefixes": [
            "docs/releases/development-skills-architecture-v0-3-vit/",
            "docs/releases/development-skills-v0-3/",
        ],
        "control_prefixes": [
            "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7/",
            "registries/implementation/dsai3v_cipr_rac/",
        ],
        "allowed_ops": ["ADD", "MODIFY"],
        "baseline_certificate_path": "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7/DSAI3V_RAC_PILOT_BASELINE_CERTIFICATE_v0_1.json",
    }


def _baseline(surface: str = "b" * 64) -> dict:
    value = {
        "schema": PILOT_BASELINE_SCHEMA,
        "policy_id": "DSAI3V-RAC-PILOT-POLICY-v0.1",
        "operator_decision_id": "a" * 64,
        "source_commit_sha": "c" * 40,
        "source_tree_sha": "d" * 40,
        "assurance_surface_id": surface,
        "reference_status": "PASS",
        "reference_source": "EXACT_FULL_REFERENCE_REQUIRED_BEFORE_ACTIVATION",
    }
    value["baseline_id"] = canonical_sha256(value, role="OVC_RAC_PILOT_BASELINE")
    return value


def _lineage(path: str, op: str = "ADD") -> dict:
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "EXAMPLE",
        "packet_id": "EXAMPLE-WP1",
        "logical_changes": [
            {"op": op, "path": path, "mode": "100644", "blob_sha": "e" * 40}
        ],
        "authority_manifest_id": "1" * 64,
        "dependency_frontier_id": "2" * 64,
        "completion_transition": {"status": "COMPLETED"},
    }
    return build_vit_payload_lineage_record(
        programme_id="EXAMPLE",
        packet_id="EXAMPLE-WP1",
        pip_identity_payload=pip,
    )


class TestRacBoundedPilot(unittest.TestCase):
    def test_inactive_policy_falls_back(self) -> None:
        result = classify_candidate(
            root=ROOT,
            candidate_head_sha="f" * 40,
            lineage_record=_lineage(
                "docs/releases/development-skills-v0-3/example/EXAMPLE_RECEIPT_v0_1.json"
            ),
            policy=_policy("INSTALLED_INACTIVE_BASELINE_REQUIRED"),
            baseline=None,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "POLICY_INACTIVE")

    @patch("ovc.development.skills.repository_assurance_pilot.assurance_surface_id", return_value="b" * 64)
    def test_exact_receipt_only_surface_match_is_eligible(self, _surface) -> None:
        result = classify_candidate(
            root=ROOT,
            candidate_head_sha="f" * 40,
            lineage_record=_lineage(
                "docs/releases/development-skills-architecture-v0-3-vit/example/EXAMPLE_MERGE_RECEIPT_v0_1.json"
            ),
            policy=_policy(),
            baseline=_baseline(),
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["pilot_class"], PILOT_CLASS)

    @patch("ovc.development.skills.repository_assurance_pilot.assurance_surface_id", return_value="b" * 64)
    def test_code_change_cannot_enter_pilot(self, _surface) -> None:
        result = classify_candidate(
            root=ROOT,
            candidate_head_sha="f" * 40,
            lineage_record=_lineage("src/ovc/development/skills/vit_routing.py", "MODIFY"),
            policy=_policy(),
            baseline=_baseline(),
        )
        self.assertFalse(result["eligible"])
        self.assertTrue(result["reason"].startswith("PATH_NOT_RECEIPT_ONLY:"))

    @patch("ovc.development.skills.repository_assurance_pilot.assurance_surface_id", return_value="b" * 64)
    def test_delete_fails_to_canonical_fallback(self, _surface) -> None:
        result = classify_candidate(
            root=ROOT,
            candidate_head_sha="f" * 40,
            lineage_record=_lineage(
                "docs/releases/development-skills-v0-3/example/EXAMPLE_RECEIPT.json",
                "DELETE",
            ),
            policy=_policy(),
            baseline=_baseline(),
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "OP_NOT_ALLOWED:DELETE")

    @patch("ovc.development.skills.repository_assurance_pilot.assurance_surface_id", return_value="9" * 64)
    def test_surface_drift_fails_to_canonical_fallback(self, _surface) -> None:
        result = classify_candidate(
            root=ROOT,
            candidate_head_sha="f" * 40,
            lineage_record=_lineage(
                "docs/releases/development-skills-v0-3/example/EXAMPLE_RECEIPT.json"
            ),
            policy=_policy(),
            baseline=_baseline(),
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "ASSURANCE_SURFACE_DRIFT")

    def test_certificate_requires_all_receipts_verified(self) -> None:
        classification = {
            "eligible": True,
            "pip_id": "1" * 64,
            "baseline_id": "2" * 64,
            "candidate_assurance_surface_id": "3" * 64,
            "receipt_paths": ["docs/releases/development-skills-v0-3/x/X_RECEIPT.json"],
        }
        with self.assertRaisesRegex(RepositoryAssurancePilotError, "RAC_PILOT_RECEIPT_VERIFICATION_INCOMPLETE"):
            build_pilot_certificate(
                candidate_head_sha="4" * 40,
                candidate_tree_sha="5" * 40,
                classification=classification,
                policy=_policy(),
                verified_receipt_paths=[],
            )

    def test_pilot_selection_uses_existing_pr_listener_without_new_workflow(self) -> None:
        tiered = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text(encoding="utf-8")
        selector = (ROOT / "tools/ci/prvitr_rac_ready.py").read_text(encoding="utf-8")
        self.assertFalse((ROOT / ".github/workflows/rac-delta-assurance-pilot.yml").exists())
        self.assertIn("run: python3 tools/ci/prvitr_rac_ready.py", tiered)
        self.assertIn("return live.command_ready()", selector)
        self.assertIn("build_pilot_certificate", selector)
        self.assertNotIn("_branch_sha(base_ref)", selector)

    def test_live_workflow_preserves_exact_final_gateway(self) -> None:
        tiered = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text(encoding="utf-8")
        self.assertIn("run: python3 tools/ci/prvitr_rac_ready.py", tiered)
        self.assertIn("run: python3 tools/ci/prvitr_live_admission.py acquire", tiered)
        self.assertIn("run: python3 tools/ci/prvitr_live_admission.py finalize", tiered)
        policy = json.loads((ROOT / "registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "ACTIVE_BOUNDED_PILOT")
        self.assertEqual(policy["pilot_class"], PILOT_CLASS)
        self.assertEqual(
            policy["reference_reconciliation"],
            "EXISTING_TESTS_WORKFLOW_CONCURRENT_ORACLE",
        )
        self.assertEqual(policy["general_gate"], "DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL")


if __name__ == "__main__":
    unittest.main()
