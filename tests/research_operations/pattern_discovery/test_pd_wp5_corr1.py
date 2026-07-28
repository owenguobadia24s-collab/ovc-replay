from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import unittest

from apps.research_console.pattern_discovery import (
    CORRECTION_BANNER,
    REVIEW_DISPOSITIONS,
    review_fields_for_disposition,
)
from ovc.research_operations.pattern_discovery.review_corrections import (
    PILOT_CORRECTION_SPECS,
    PILOT_RUN_ID,
    REVIEW_SCHEMA_V2,
    ReviewCorrectionError,
    build_corrected_review_projection,
    build_correction_ledger,
    canonical_sha256,
    validate_review_decision_v2,
    validate_review_input_v2,
)


ROOT = Path(__file__).resolve().parents[3]
GATE_ROOT = ROOT / "docs/releases/pattern-discovery-v0-3/pd-g5p"
CORR_ROOT = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1"
LEDGER_PATH = CORR_ROOT / "PD_WP5_CORR1_CORRECTION_LEDGER.json"
IDENTITY_PATH = CORR_ROOT / "PD_WP5_CANONICAL_IDENTITY_RESET_PROCEDURE_CANDIDATE.json"
CONTRACT_PATH = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_FINAL_CANONICAL_DISCOVERY_CONTRACT_CANDIDATE_v0_2.md"
REVIEW_SCHEMA_PATH = ROOT / "schemas/research_operations/pattern_discovery/pd_wp5_pilot_review_input_v0_2.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "schemas/research_operations/pattern_discovery/pd_wp5_pilot_review_receipt_v0_2.schema.json"
LEDGER_SCHEMA_PATH = ROOT / "schemas/research_operations/pattern_discovery/pd_wp5_correction_ledger_v0_1.schema.json"


def exact_bytes(name: str) -> bytes:
    encoded = (GATE_ROOT / "evidence/raw" / f"{name}.b64").read_text(encoding="ascii").strip()
    return base64.b64decode(encoded, validate=True)


def exact_json(name: str) -> dict:
    value = json.loads(exact_bytes(name).decode("utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(name)
    return value


def complete_decision(candidate_id: str, disposition: str) -> dict:
    common = {
        "candidate_window_id": candidate_id,
        "review_disposition": disposition,
        "notes": "structured fixture review",
        "evidence_references": ["fixture/evidence.json"],
        "ui_friction_codes": [],
    }
    if disposition == "WORKFLOW_ACCEPTED":
        return {**common, "acceptance_basis": "No blocking workflow or interface defect.", "acceptance_criteria": ["Required evidence is present."]}
    spec = dict(PILOT_CORRECTION_SPECS[candidate_id])
    spec.pop("review_disposition", None)
    spec.pop("acceptance_test_ids", None)
    return {**common, **spec}


class PdWp5Corr1Tests(unittest.TestCase):
    def test_preserved_signed_sources_are_byte_identical(self) -> None:
        expected = {
            "pilot-review-receipt.json": "2486d9f7097c434fd52d4d5fd0cd086df8117887b6bf4b70a9ef6cf50869ab81",
            "pilot-defect-ledger.json": "a9e0102e042e3919871c7c0b135a60e4d3d27d8483f2e8eaa55fd366ee6d174d",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256(exact_bytes(name)).hexdigest(), digest)

    def test_static_correction_ledger_is_exactly_reproducible(self) -> None:
        static = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        generated = build_correction_ledger()
        self.assertEqual(static, generated)
        body = dict(static)
        claimed = body.pop("ledger_sha256")
        self.assertEqual(canonical_sha256(body), claimed)
        self.assertEqual(static["entry_count"], 5)
        self.assertEqual({item["candidate_window_id"] for item in static["entries"]}, set(PILOT_CORRECTION_SPECS))
        self.assertEqual(static["second_pilot_replay_recommendation"], "NOT_REQUIRED")
        self.assertFalse(static["second_pilot_replay_authorised"])
        self.assertFalse(static["canonical_discovery_authorised"])

    def test_corrected_projection_is_read_only_and_deterministic(self) -> None:
        receipt = exact_json("pilot-review-receipt.json")
        first = build_corrected_review_projection(receipt)
        second = build_corrected_review_projection(json.loads(json.dumps(receipt, sort_keys=True)))
        self.assertEqual(first, second)
        self.assertEqual(first["row_count"], 5)
        self.assertFalse(first["source_artifacts_mutated"])
        self.assertFalse(first["second_pilot_replay_required"])
        self.assertFalse(first["canonical_discovery_authorised"])
        self.assertTrue(all(row["pilot_only"] for row in first["rows"]))
        self.assertTrue(all(row["canonical_append"] == "DENIED" for row in first["rows"]))

    def test_v2_workflow_defect_fails_closed(self) -> None:
        candidate_id = "PDPILOT-CANDIDATE-bf1e96ba941e97a4d12e8fba"
        incomplete = {
            "candidate_window_id": candidate_id,
            "review_disposition": "FLAG_WORKFLOW_DEFECT",
            "notes": "generic note",
            "evidence_references": ["fixture/evidence.json"],
            "ui_friction_codes": [],
        }
        with self.assertRaisesRegex(ReviewCorrectionError, "WORKFLOW_DEFECT_INCOMPLETE"):
            validate_review_decision_v2(incomplete)
        complete = complete_decision(candidate_id, "FLAG_WORKFLOW_DEFECT")
        normalized = validate_review_decision_v2(complete)
        self.assertEqual(normalized["finding_code"], "PD-WF-STRUCTURED-DEFECT-EVIDENCE-MISSING-001")

    def test_v2_ui_friction_requires_code_and_surface(self) -> None:
        candidate_id = "PDPILOT-CANDIDATE-f10546a0a1ec4dfbe03545c4"
        complete = complete_decision(candidate_id, "FLAG_UI_FRICTION")
        complete["ui_friction_codes"] = []
        with self.assertRaisesRegex(ReviewCorrectionError, "UI_FRICTION_INCOMPLETE"):
            validate_review_decision_v2(complete)
        complete["ui_friction_codes"] = ["PD-UI-REVIEW-CONTEXT-MISSING-001"]
        self.assertEqual(validate_review_decision_v2(complete)["affected_console_surface"], "Candidate Detail / Review action candidate")

    def test_v2_defer_and_reject_require_resolution_or_structural_basis(self) -> None:
        defer_id = "PDPILOT-CANDIDATE-1ae851d7446f3934e18248dc"
        defer = complete_decision(defer_id, "DEFER_PILOT_OBJECT")
        defer.pop("resolution_criteria")
        with self.assertRaisesRegex(ReviewCorrectionError, "DEFER_REVIEW_INCOMPLETE"):
            validate_review_decision_v2(defer)

        reject_id = "PDPILOT-CANDIDATE-4c78ddd97117f06a0c6a1339"
        reject = complete_decision(reject_id, "REJECT_PILOT_OBJECT")
        reject.pop("structural_basis")
        with self.assertRaisesRegex(ReviewCorrectionError, "REJECT_REVIEW_INCOMPLETE"):
            validate_review_decision_v2(reject)

    def test_complete_v2_review_is_order_independent(self) -> None:
        accepted_id = "PDPILOT-CANDIDATE-b6b4de1660fa62cc2321ba46"
        decisions = [complete_decision(candidate_id, spec["review_disposition"]) for candidate_id, spec in PILOT_CORRECTION_SPECS.items()]
        decisions.append(complete_decision(accepted_id, "WORKFLOW_ACCEPTED"))
        review = {
            "schema": REVIEW_SCHEMA_V2,
            "pilot_run_id": PILOT_RUN_ID,
            "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "reviewed_at_utc": "2026-07-28T15:00:00Z",
            "decisions": decisions,
        }
        expected = [item["candidate_window_id"] for item in decisions]
        first = validate_review_input_v2(review, expected_candidate_ids=expected, pilot_run_id=PILOT_RUN_ID)
        second = validate_review_input_v2({**review, "decisions": list(reversed(decisions))}, expected_candidate_ids=expected, pilot_run_id=PILOT_RUN_ID)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)

    def test_console_fields_match_v2_contract_and_remain_non_authoritative(self) -> None:
        self.assertIn("C2 AND CANONICAL AUTHORITY UNCHANGED", CORRECTION_BANNER)
        self.assertEqual(set(REVIEW_DISPOSITIONS), {
            "WORKFLOW_ACCEPTED", "FLAG_WORKFLOW_DEFECT", "FLAG_UI_FRICTION", "DEFER_PILOT_OBJECT", "REJECT_PILOT_OBJECT"
        })
        self.assertIn("affected_console_surface", review_fields_for_disposition("FLAG_UI_FRICTION"))
        self.assertIn("resolution_criteria", review_fields_for_disposition("DEFER_PILOT_OBJECT"))
        self.assertIn("structural_basis", review_fields_for_disposition("REJECT_PILOT_OBJECT"))

    def test_contract_schemas_and_identity_reset_remain_fail_closed(self) -> None:
        for path in (REVIEW_SCHEMA_PATH, RECEIPT_SCHEMA_PATH, LEDGER_SCHEMA_PATH):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(identity["status"], "CANDIDATE_ONLY_NOT_AUTHORISED")
        self.assertEqual(identity["pilot_identity_reuse"], "DENIED")
        self.assertFalse(identity["canonical_run_authorised"])
        self.assertFalse(identity["second_pilot_replay_authorised"])
        self.assertEqual(identity["canonical_append"], "DENIED")
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_ONLY_NOT_AUTHORISED", contract)
        self.assertIn("Activation requires a new explicit operator decision", contract)


if __name__ == "__main__":
    unittest.main()
