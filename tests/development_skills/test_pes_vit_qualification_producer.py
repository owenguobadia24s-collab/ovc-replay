from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from ovc.development.skills.pes_vit_qualification_producer import (
    PesVitQualificationProducerError,
    PRODUCER_ACTIVATION_GATE,
    PRODUCER_ACTIVATION_PHRASE,
    PRODUCER_DISPATCH_ACTION,
    PRODUCER_DISPATCH_WRITE_DOMAIN,
    PRODUCER_SEMANTIC_OWNER,
    PRODUCER_TARGET_LEDGER_BRANCH,
    PRODUCER_TARGET_LEDGER_ROOT,
    PRODUCER_WRITE_SCOPE,
    build_producer_dispatch,
    build_qualification_publication_request,
    validate_producer_activation,
    validate_producer_dispatch,
    validate_qualification_publication_request,
)
from ovc.development.skills.vit_routing import build_vit_payload_lineage_record
import tools.ci.pes_vit_qualification_producer as producer_cli


ISSUER = "OVC-SKILL-030|PACKET_EXECUTION|trusted-test-runtime"
ROOT = Path(__file__).resolve().parents[2]
ACTIVATION_PACKET = ROOT / "docs/releases/development-skills-v0-3/pes-vit-liveness/PES_VIT_QUALIFICATION_PRODUCER_ACTIVATION_PACKET_v0_1.json"


def _rehash(record: dict, identity_key: str) -> dict:
    payload = {key: value for key, value in record.items() if key != identity_key}
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    record[identity_key] = hashlib.sha256(raw).hexdigest()
    return record


def _lineage(path: str = "example.txt"):
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "TEST-PROGRAMME",
        "packet_id": "TEST-PACKET",
        "logical_changes": [
            {
                "op": "ADD",
                "path": path,
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


def _activation():
    payload = {
        "schema_version": "ovc-pes-vit-qualification-producer-runtime-activation/v0.1",
        "gate_id": PRODUCER_ACTIVATION_GATE,
        "decision": "PASS",
        "operator_phrase": PRODUCER_ACTIVATION_PHRASE,
        "status": "ACTIVE",
        "authority_effect": "BOUNDED_INFRASTRUCTURE_ACTIVATION",
        "executor_scope": "TRUSTED_OWNER_ISSUED_REQUEST_ONLY",
        "target": {
            "ledger_branch": PRODUCER_TARGET_LEDGER_BRANCH,
            "ledger_root": PRODUCER_TARGET_LEDGER_ROOT,
            "write_scope": PRODUCER_WRITE_SCOPE,
        },
        "capabilities": {
            "ledger_write": True,
            "persistent_dispatch": True,
            "event_subscription": False,
            "polling": False,
            "direct_main_write": False,
            "merge": False,
            "force_push": False,
            "history_rewrite": False,
            "programme_authority": False,
            "vit_authority": False,
            "siq_authority": False,
            "grt_authority": False,
        },
    }
    return _rehash(payload, "activation_id")


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
        _rehash(request, "request_id")
        with self.assertRaisesRegex(PesVitQualificationProducerError, "AUTHORITY_ID_MISMATCH"):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_target_drift_fails_closed(self) -> None:
        request = dict(self._request())
        request["target"] = dict(request["target"])
        request["target"]["ledger_branch"] = "main"
        _rehash(request, "request_id")
        with self.assertRaisesRegex(PesVitQualificationProducerError, "LEDGER_BRANCH_INVALID"):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_owner_authority_must_be_durable_not_pr_metadata(self) -> None:
        request = dict(self._request())
        request["issuance"] = dict(request["issuance"])
        request["issuance"]["owner_authority_source_kind"] = "PR_BODY"
        _rehash(request, "request_id")
        with self.assertRaisesRegex(
            PesVitQualificationProducerError,
            "OWNER_AUTHORITY_SOURCE_KIND_INVALID",
        ):
            validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            )

    def test_materialized_activation_packet_is_canonical_and_exact(self) -> None:
        raw = ACTIVATION_PACKET.read_bytes()
        packet = json.loads(raw.decode("utf-8"))
        canonical = json.dumps(
            packet,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(raw, canonical)
        self.assertEqual(packet["operator_decision"]["phrase"], PRODUCER_ACTIVATION_PHRASE)
        self.assertEqual(
            packet["authority_manifest_id"],
            hashlib.sha256(
                json.dumps(
                    packet["authority_manifest"],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
        )
        self.assertEqual(
            packet["dependency_frontier_id"],
            hashlib.sha256(
                json.dumps(
                    packet["dependency_frontier"],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
        )
        validate_producer_activation(packet["runtime_activation"])

    def test_operator_activation_is_exact_and_preserves_permanent_denials(self) -> None:
        activation = validate_producer_activation(_activation())
        self.assertEqual(activation.gate_id, PRODUCER_ACTIVATION_GATE)
        self.assertEqual(activation.ledger_branch, PRODUCER_TARGET_LEDGER_BRANCH)
        self.assertNotEqual(activation.ledger_branch, "main")

    def test_activation_target_or_capability_widening_fails_closed(self) -> None:
        activation = _activation()
        activation["capabilities"] = dict(activation["capabilities"])
        activation["capabilities"]["merge"] = True
        _rehash(activation, "activation_id")
        with self.assertRaisesRegex(PesVitQualificationProducerError, "CAPABILITY_DRIFT"):
            validate_producer_activation(activation)

    def test_dispatch_is_bound_to_request_activation_executor_domain_and_fence(self) -> None:
        request = self._request()
        activation = _activation()
        dispatch = build_producer_dispatch(
            request=request,
            activation=activation,
            expected_issuer_identity=ISSUER,
            fencing_generation=7,
        )
        self.assertEqual(dispatch["action"], PRODUCER_DISPATCH_ACTION)
        self.assertEqual(dispatch["write_domain"], PRODUCER_DISPATCH_WRITE_DOMAIN)
        self.assertEqual(dispatch["semantic_owner"], PRODUCER_SEMANTIC_OWNER)
        validated = validate_producer_dispatch(
            dispatch,
            request=validate_qualification_publication_request(
                request,
                expected_issuer_identity=ISSUER,
            ),
            activation=validate_producer_activation(activation),
            expected_fencing_generation=7,
        )
        self.assertEqual(validated.fencing_generation, 7)

    def test_stale_dispatch_fence_fails_closed(self) -> None:
        request = self._request()
        activation = _activation()
        dispatch = build_producer_dispatch(
            request=request,
            activation=activation,
            expected_issuer_identity=ISSUER,
            fencing_generation=7,
        )
        with self.assertRaisesRegex(PesVitQualificationProducerError, "STALE_FENCE"):
            validate_producer_dispatch(
                dispatch,
                request=validate_qualification_publication_request(
                    request,
                    expected_issuer_identity=ISSUER,
                ),
                activation=validate_producer_activation(activation),
                expected_fencing_generation=8,
            )

    def test_active_publish_is_ledger_only_and_idempotent_store_owned(self) -> None:
        request = self._request()
        activation = _activation()
        dispatch = build_producer_dispatch(
            request=request,
            activation=activation,
            expected_issuer_identity=ISSUER,
            fencing_generation=9,
        )
        envelope = {
            "qualification_id": "d" * 64,
            "pip_id": request["pip_id"],
            "authority_manifest_id": request["authority_manifest_id"],
            "dependency_frontier_id": request["dependency_frontier_id"],
        }
        with mock.patch.object(
            producer_cli,
            "prepare_shadow_envelope",
            return_value=envelope,
        ), mock.patch.object(
            producer_cli,
            "publish_qualification_envelope",
            return_value="d" * 64,
        ) as publish:
            result = producer_cli.publish_authorised_request(
                repo=Path("."),
                request=request,
                activation=activation,
                dispatch=dispatch,
                expected_issuer_identity=ISSUER,
                expected_fencing_generation=9,
            )
        publish.assert_called_once_with(envelope)
        self.assertEqual(result["qualification_id"], "d" * 64)
        self.assertEqual(result["ledger_branch"], PRODUCER_TARGET_LEDGER_BRANCH)
        self.assertEqual(result["authority_effect"], "NONE_EXECUTE_AUTHORISED_OWNER_REQUEST")

    def test_stale_fence_blocks_before_ledger_actuator(self) -> None:
        request = self._request()
        activation = _activation()
        dispatch = build_producer_dispatch(
            request=request,
            activation=activation,
            expected_issuer_identity=ISSUER,
            fencing_generation=3,
        )
        with mock.patch.object(producer_cli, "publish_qualification_envelope") as publish:
            with self.assertRaisesRegex(PesVitQualificationProducerError, "STALE_FENCE"):
                producer_cli.publish_authorised_request(
                    repo=Path("."),
                    request=request,
                    activation=activation,
                    dispatch=dispatch,
                    expected_issuer_identity=ISSUER,
                    expected_fencing_generation=4,
                )
        publish.assert_not_called()

    def test_active_cli_has_no_main_or_merge_actuator(self) -> None:
        self.assertTrue(callable(producer_cli.publish_authorised_request))
        self.assertFalse(hasattr(producer_cli, "merge_pull_request"))
        self.assertFalse(hasattr(producer_cli, "write_main"))
        self.assertFalse(hasattr(producer_cli, "force_push"))

    def test_diasi_selected_class_is_fenced_before_pes_envelope_or_publish(self) -> None:
        request = build_qualification_publication_request(
            candidate_head_sha="1" * 40,
            lineage_record=_lineage(
                "docs/releases/development-skills-v0-3/dias/EXACT_SELECTED_RECEIPT.json"
            ),
            issuer_identity=ISSUER,
            owner_authority_source="records/owner/authority.json@blob:abc123",
        )
        with mock.patch.object(producer_cli, "build_qualification_envelope") as build:
            with self.assertRaisesRegex(RuntimeError, "SELECTED_CLASS_OLD_ROUTE_FENCED"):
                producer_cli.prepare_shadow_envelope(
                    repo=ROOT,
                    request=request,
                    expected_issuer_identity=ISSUER,
                )
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
