from __future__ import annotations

import hashlib
import json
import unittest

from ovc.development.skills.pes.vit_qualification_producer import (
    PesVitQualificationProducerError,
    PRODUCER_TARGET_LEDGER_BRANCH,
    PRODUCER_TARGET_LEDGER_ROOT,
    PRODUCER_WRITE_SCOPE,
    build_qualification_publication_request,
    validate_qualification_publication_request,
)
from ovc.development.skills.vit_routing import build_vit_payload_lineage_record
import tools.ci.pes_vit_qualification_producer as producer_cli


ISSUER = "OVC-SKILL-030|PACKET_EXECUTION|trusted-test-runtime"


def _rehash(record: dict) -> dict:
    payload = {key: value for key, value in record.items() if key != "request_id"}
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    record["request_id"] = hashlib.sha256(raw).hexdigest()
    return record


def _lineage():
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "TEST-PROGRAMME",
        "packet_id": "TEST-PACKET",
        "logical_changes": [
            {
                "op": "ADD",
                "path": "example.txt",
                "blob_sha": "2" * 40,
                "mode": "100644",
            }
        ],
        "authority_manifest_id": "a" * 64,
        "dependency_frontier_id": "b" * 64,
        "completion_transition": {"status": "COMPLETED"},
    }
    return build_vit_payload_lineage_record(
        programme_id="TEST-PROGRAMME",
        packet_id="TEST-PACKET",
        pip_identity_payload=pip,
    )


class PesVitQualificationProducerTests(unittest.TestCase):
    def _request(self):
        return build_qualification_publication_request(
            candidate_head_sha="1" * 40,
            lineage_record=_lineage(),
            issuer_identity=ISSUER,
            owner_authority_source="records/owner/authority.json@blob:abc123",
        )

    def test_valid_request_is_exact_authority_inert_and_ledger_scoped(self) -> None:
        request = self._request()
        validated = validate_qualification_publication_request(
            request,
            expected_issuer_identity=ISSUER,
        )
        self.assertEqual(validated.candidate_head_sha, "1" * 40)
        self.assertEqual(validated.authority_manifest_id, "a" * 64)
        self.assertEqual(validated.dependency_frontier_id, "b" * 64)
        self.assertEqual(request["authority_effect"], "NONE_REQUEST_ONLY")
        self.assertEqual(request["target"]["ledger_branch"], PRODUCER_TARGET_LEDGER_BRANCH)
        self.assertEqual(request["target"]["ledger_root"], PRODUCER_TARGET_LEDGER_ROOT)
        self.assertEqual(request["target"]["write_scope"], PRODUCER_WRITE_SCOPE)

    def test_request_mutation_invalidates_identity(self) -> None:
        request = dict(self._request())
        request["candidate_head_sha"] = "3" * 40
        with self.assertRaisesRegex(PesVitQualificationProducerError, "REQUEST_ID_MISMATCH"):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_wrong_issuer_fails_closed(self) -> None:
        with self.assertRaisesRegex(PesVitQualificationProducerError, "ISSUER_NOT_AUTHORISED"):
            validate_qualification_publication_request(
                self._request(),
                expected_issuer_identity="UNAUTHORISED",
            )

    def test_authority_identity_cannot_drift_from_owner_lineage(self) -> None:
        request = dict(self._request())
        request["authority_manifest_id"] = "c" * 64
        _rehash(request)
        with self.assertRaisesRegex(PesVitQualificationProducerError, "AUTHORITY_ID_MISMATCH"):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_target_drift_fails_closed(self) -> None:
        request = dict(self._request())
        request["target"] = dict(request["target"])
        request["target"]["ledger_branch"] = "main"
        _rehash(request)
        with self.assertRaisesRegex(PesVitQualificationProducerError, "LEDGER_BRANCH_INVALID"):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_owner_authority_must_be_durable_not_pr_metadata(self) -> None:
        request = dict(self._request())
        request["issuance"] = dict(request["issuance"])
        request["issuance"]["owner_authority_source_kind"] = "PR_BODY"
        _rehash(request)
        with self.assertRaisesRegex(PesVitQualificationProducerError, "OWNER_AUTHORITY_SOURCE_KIND_INVALID"):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_wp1_cli_exposes_no_ledger_publish_actuator(self) -> None:
        self.assertFalse(hasattr(producer_cli, "publish_qualification_envelope"))
        self.assertTrue(callable(producer_cli.prepare_shadow_envelope))


if __name__ == "__main__":
    unittest.main()
