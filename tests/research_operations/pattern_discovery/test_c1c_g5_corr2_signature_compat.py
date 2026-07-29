from __future__ import annotations

import hashlib
import json
import unittest

from ovc.research_operations.pattern_discovery import pilot_corrective_review_v2 as review_v2
from ovc.research_operations.pattern_discovery.pilot_corr2_review_closure_entry import (
    schema_aware_signature_body,
)


def logical_sha(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def signed_record(body: dict, *, inventory_id: str, status: str) -> dict:
    return {
        **body,
        "inventory_id": inventory_id,
        "signature_algorithm": "ED25519",
        "signature_format": "SSHSIG_OPENSSH_V1",
        "signature_namespace": "ovc-rps",
        "signed_payload_sha256": logical_sha(body),
        "signature_sha256": "0" * 64,
        "signature": "test-signature",
        "status": status,
    }


class C1cG5Corr2SignatureCompatibilityTests(unittest.TestCase):
    def test_structured_v2_inventory_retains_operator_binding_in_signed_body(self) -> None:
        body = {
            "schema": review_v2.INVENTORY_SCHEMA_V2,
            "pilot_run_id": review_v2.EXPECTED_RUN_ID,
            "pilot_namespace": review_v2.EXPECTED_NAMESPACE,
            "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "signing_binding_id": "RPS.SIGNING.50092c28981fef08f53a6cb5",
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        }
        record = signed_record(
            body,
            inventory_id="PD.PILOT.REVIEW-V2.EVIDENCE.test",
            status="SIGNED_STRUCTURED_V2_REVIEW_EVIDENCE_COMPLETE",
        )

        reconstructed = schema_aware_signature_body(record, inventory=True)

        self.assertEqual(reconstructed, body)
        self.assertEqual(logical_sha(reconstructed), record["signed_payload_sha256"])
        self.assertIn("operator_id", reconstructed)
        self.assertIn("signing_binding_id", reconstructed)

    def test_immutable_v1_inventory_keeps_historical_unsigned_attachment_fields(self) -> None:
        body = {
            "schema": "ovc-pd-wp5-signed-pilot-evidence-inventory/v1",
            "pilot_run_id": review_v2.EXPECTED_RUN_ID,
            "pilot_namespace": review_v2.EXPECTED_NAMESPACE,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        }
        record = signed_record(
            {
                **body,
                "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
                "signing_binding_id": "RPS.SIGNING.50092c28981fef08f53a6cb5",
            },
            inventory_id="PD.PILOT.EVIDENCE.test",
            status="SIGNED_PILOT_EVIDENCE_COMPLETE",
        )
        # Historical v1 signed_payload_sha256 excludes these attached fields.
        record["signed_payload_sha256"] = logical_sha(body)

        reconstructed = schema_aware_signature_body(record, inventory=True)

        self.assertEqual(reconstructed, body)
        self.assertEqual(logical_sha(reconstructed), record["signed_payload_sha256"])
        self.assertNotIn("operator_id", reconstructed)
        self.assertNotIn("signing_binding_id", reconstructed)

    def test_operator_entry_installs_schema_aware_verifier(self) -> None:
        self.assertIs(review_v2._signature_body, schema_aware_signature_body)


if __name__ == "__main__":
    unittest.main()
