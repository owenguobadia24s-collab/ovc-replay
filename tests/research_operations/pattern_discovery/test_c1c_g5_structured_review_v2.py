from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import unittest

from ovc.research_operations.pattern_discovery.pilot_corrective_review_v2 import (
    EXPECTED_NAMESPACE,
    EXPECTED_RUN_ID,
    _reject_placeholders,
    _signature_body,
    _verify_signature,
    build_review_template_v2,
)
from ovc.research_operations.pattern_discovery.review_corrections import (
    REVIEW_SCHEMA_V2,
    ReviewCorrectionError,
    validate_review_input_v2,
)


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/structured-review-v2"
RAW = EVIDENCE_ROOT / "evidence/raw"
INDEX = EVIDENCE_ROOT / "C1C_G5_CORRECTIVE_V2_EVIDENCE_INDEX.json"
PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOjITxMioIXgGbApGohaq2J/dQltuluVvPzy5B3I3QKJ"


def exact_bytes(name: str) -> bytes:
    encoded = "".join((RAW / f"{name}.b64").read_text(encoding="ascii").split())
    return base64.b64decode(encoded, validate=True)


def exact_json(name: str) -> dict:
    value = json.loads(exact_bytes(name).decode("utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(name)
    return value


def complete_decision(template: dict) -> dict:
    disposition = template["review_disposition"]
    item = {
        "candidate_window_id": template["candidate_window_id"],
        "review_disposition": disposition,
        "notes": "Structured review evidence completed for the corrective v2 pilot.",
        "evidence_references": ["review/console-bundle.json", "review/queue-items.jsonl"],
        "ui_friction_codes": [],
    }
    if disposition == "WORKFLOW_ACCEPTED":
        item.update({
            "acceptance_basis": "No blocking workflow or interface defect is present for this pilot object.",
            "acceptance_criteria": ["Required review evidence is visible and reproducible."],
        })
    elif disposition == "FLAG_WORKFLOW_DEFECT":
        item.update({
            "finding_code": "PD-WF-CORRECTIVE-REVIEW-001",
            "affected_component": "pilot_corrective_review_v2.finalize",
            "actual_behavior": "The original v1 finalizer accepted an unstructured defect record.",
            "expected_behavior": "The v2 finalizer rejects incomplete structured defect evidence.",
            "reproduction_steps": ["Submit an incomplete FLAG_WORKFLOW_DEFECT decision."],
            "acceptance_criteria": ["Incomplete structured defect evidence is rejected."],
        })
    elif disposition == "FLAG_UI_FRICTION":
        item.update({
            "finding_code": "PD-UI-CORRECTIVE-REVIEW-001",
            "ui_friction_codes": ["PD-UI-CORRECTIVE-REVIEW-001"],
            "affected_component": "apps.research_console.pattern_discovery",
            "affected_console_surface": "Candidate Detail / Review action candidate",
            "actual_behavior": "The v1 review omitted a structured UI-friction code.",
            "expected_behavior": "The v2 review requires a code and affected Console surface.",
            "reproduction_steps": ["Submit FLAG_UI_FRICTION without a PD-UI code."],
            "acceptance_criteria": ["The v2 validator rejects missing UI-friction codes."],
        })
    elif disposition == "DEFER_PILOT_OBJECT":
        item.update({
            "finding_code": "PD-DEFER-CORRECTIVE-REVIEW-001",
            "resolution_criteria": ["The named evidence condition is resolved."],
            "next_review_condition": "Re-review only after the resolution criterion is evidenced.",
        })
    elif disposition == "REJECT_PILOT_OBJECT":
        item.update({
            "finding_code": "PD-REJECT-CORRECTIVE-REVIEW-001",
            "structural_basis": "The exclusion is based solely on a reproducible workflow or structural condition.",
        })
    else:
        raise AssertionError(disposition)
    return item


class C1cG5StructuredReviewV2Tests(unittest.TestCase):
    def test_exact_compact_bytes_and_hash_chain(self) -> None:
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(index["pilot_run_id"], EXPECTED_RUN_ID)
        self.assertEqual(index["pilot_namespace"], EXPECTED_NAMESPACE)
        for item in index["compact_files"]:
            payload = exact_bytes(item["name"])
            self.assertEqual(len(payload), item["size_bytes"], item["name"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"], item["name"])

        inventory = exact_json("signed-pilot-evidence-inventory.json")
        self.assertEqual(inventory["pilot_run_file_sha256"], hashlib.sha256(exact_bytes("pilot-run.json")).hexdigest())
        self.assertEqual(inventory["pilot_output_manifest_file_sha256"], hashlib.sha256(exact_bytes("output-manifest.json")).hexdigest())
        self.assertEqual(inventory["pilot_review_receipt_file_sha256"], hashlib.sha256(exact_bytes("pilot-review-receipt.json")).hexdigest())
        self.assertEqual(inventory["pilot_defect_ledger_file_sha256"], hashlib.sha256(exact_bytes("pilot-defect-ledger.json")).hexdigest())
        gate = exact_json("pd-g5p-gate-input.json")
        self.assertEqual(gate["signed_pilot_evidence_inventory_file_sha256"], hashlib.sha256(exact_bytes("signed-pilot-evidence-inventory.json")).hexdigest())

    def test_ed25519_signatures_verify(self) -> None:
        run = exact_json("pilot-run.json")
        review = exact_json("pilot-review-receipt.json")
        inventory = exact_json("signed-pilot-evidence-inventory.json")
        _verify_signature(run, _signature_body(run), public_key=PUBLIC_KEY)
        _verify_signature(review, _signature_body(review), public_key=PUBLIC_KEY)
        _verify_signature(inventory, _signature_body(inventory, inventory=True), public_key=PUBLIC_KEY)

    def test_machine_rerun_is_exact_c2_v2_and_nonactivating(self) -> None:
        run = exact_json("pilot-run.json")
        manifest = exact_json("output-manifest.json")
        gate = exact_json("pd-g5p-gate-input.json")
        self.assertEqual(run["authority_gate"], "C1C-G5")
        self.assertEqual(run["next_gate"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertEqual(run["code_commit"], "0c687101e031b404b3994c8bb96d65b177f97743")
        self.assertEqual(run["pilot_namespace"], EXPECTED_NAMESPACE)
        self.assertEqual(run["derived_bundle_sha256"], run["deterministic_rerun_sha256"])
        self.assertTrue(run["deterministic_rerun_match"])
        self.assertFalse(run["provider_network_access_performed"])
        self.assertEqual(manifest["canonical_append"], "DENIED")
        self.assertEqual(gate["canonical_append"], "DENIED")
        self.assertFalse(gate["canonical_discovery_population"])

    def test_uploaded_v1_review_fails_closed_under_v2_contract(self) -> None:
        review = exact_json("pilot-review-receipt.json")
        self.assertTrue(all(not str(item.get("notes") or "").strip() for item in review["decisions"]))
        ui = [item for item in review["decisions"] if item["review_disposition"] == "FLAG_UI_FRICTION"]
        self.assertEqual(len(ui), 1)
        self.assertEqual(ui[0]["ui_friction_codes"], [])
        with self.assertRaisesRegex(ReviewCorrectionError, "INVALID_REVIEW_V2_SCHEMA"):
            validate_review_input_v2(
                review,
                expected_candidate_ids=[item["candidate_window_id"] for item in review["decisions"]],
                pilot_run_id=EXPECTED_RUN_ID,
            )

    def test_template_and_complete_v2_review_are_deterministic(self) -> None:
        review_v1 = exact_json("pilot-review-receipt.json")
        template = build_review_template_v2(review_v1)
        self.assertEqual(template["schema"], REVIEW_SCHEMA_V2)
        self.assertEqual(template["pilot_run_id"], EXPECTED_RUN_ID)
        self.assertEqual(len(template["decisions"]), 6)
        with self.assertRaisesRegex(Exception, "STRUCTURED_REVIEW_PLACEHOLDER_OR_EMPTY"):
            _reject_placeholders(template)

        completed = {
            "schema": REVIEW_SCHEMA_V2,
            "pilot_run_id": EXPECTED_RUN_ID,
            "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "reviewed_at_utc": "2026-07-28T21:00:00Z",
            "decisions": [complete_decision(item) for item in template["decisions"]],
        }
        _reject_placeholders(completed)
        expected = [item["candidate_window_id"] for item in completed["decisions"]]
        first = validate_review_input_v2(completed, expected_candidate_ids=expected, pilot_run_id=EXPECTED_RUN_ID)
        second = validate_review_input_v2({**completed, "decisions": list(reversed(completed["decisions"]))}, expected_candidate_ids=expected, pilot_run_id=EXPECTED_RUN_ID)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)

    def test_contract_and_schemas_preserve_authority_boundary(self) -> None:
        contract = (ROOT / "contracts/research_operations/pattern_discovery/C1C_G5_STRUCTURED_CORRECTIVE_REVIEW_CONTRACT_v0_1.md").read_text(encoding="utf-8")
        self.assertIn("does not execute another market replay", contract)
        self.assertIn("canonical Discovery processing or append authority", contract)
        for name in (
            "pd_wp5_pilot_review_input_v0_2.schema.json",
            "pd_wp5_pilot_review_receipt_v0_2.schema.json",
            "c1c_g5_corrective_review_defect_ledger_v0_1.schema.json",
            "c1c_g5_corrective_review_evidence_inventory_v0_1.schema.json",
            "c1c_g5_corrective_pilot_review_gate_input_v0_1.schema.json",
        ):
            schema = json.loads((ROOT / "schemas/research_operations/pattern_discovery" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main()
