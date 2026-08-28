from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ovc.development.dsai3v_completion_observability import (
    CANONICAL_COMPLETION_SCHEMA,
    build_canonical_completion_latency_receipt,
)
from ovc.development.dsai3v_completion_observability_v2 import (
    ATTACHMENT_SCHEMA_V2,
    CANONICAL_COMPLETION_SCHEMA_V2,
    TIMING_FIELDS,
    build_canonical_completion_latency_receipt_v2,
    build_completion_attachment_v2,
    normalize_canonical_utc,
    validate_canonical_completion_latency_receipt_v2,
    validate_compatible_canonical_completion_receipt,
)
from ovc.development.skills.vit_completion_runtime import persist_physical_completion
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    ReceiptStore,
)

ROOT = Path(__file__).resolve().parents[2]
FROZEN_V1_ID = "3d17ae4908a3edd3d16b038a79470fb0bd11e9913495913760f5a79e57925168"


def source(field: str, source_type: str, source_id: str, at: str) -> dict[str, str]:
    return {
        "field": field,
        "source_type": source_type,
        "source_id": source_id,
        "observed_at_utc": at,
        "authority": "OBSERVATIONAL_ONLY",
    }


class CanonicalCompletionReceiptV2Tests(unittest.TestCase):
    def v1(self) -> dict:
        return build_canonical_completion_latency_receipt(
            programme_id="OVC-DSAI-VIT-v0.3",
            packet_id="DSAI3V-FROZEN-V1-FIXTURE",
            completion_receipt_id="completion-fixture",
        )

    def sources(self) -> list[dict[str, str]]:
        rows = [
            ("pr_opened_at_utc", "GITHUB_PR", "pr:1", "2026-08-28T08:00:00Z"),
            ("aa0_reuse_observed_at_utc", "GITHUB_WORKFLOW_JOB", "job:aa0", "2026-08-28T08:00:10Z"),
            ("profile_passed_at_utc", "GITHUB_WORKFLOW_JOB", "job:profile", "2026-08-28T08:00:20Z"),
            ("siq_ready_at_utc", "GITHUB_CHECK_RUN", "check:siq", "2026-08-28T08:00:30Z"),
            ("merge_readiness_passed_at_utc", "GITHUB_CHECK_RUN", "check:merge", "2026-08-28T08:00:40Z"),
            ("physical_materialised_at_utc", "GITHUB_PR", "pr:1", "2026-08-28T08:00:50Z"),
            ("packet_completion_receipt_persisted_at_utc", "PACKET_COMPLETION_RECEIPT", "completion", "2026-08-28T08:00:51.1Z"),
            ("completion_proof_persisted_at_utc", "COMPLETION_PROOF", "proof", "2026-08-28T08:00:51.123456Z"),
        ]
        return [source(*row) for row in rows]

    def aa0(self) -> dict:
        return {
            "repository_assurance_disposition": "EXACT_GENERATION_REUSE",
            "unittest_parity_disposition": "EXACT_GENERATION_REUSE",
            "runner_parity_disposition": "EXACT_GENERATION_REUSE",
            "canonical_shards_executed": False,
            "candidate_head_sha": "a" * 40,
            "pr_head_sha": "a" * 40,
            "pip_id": "b" * 64,
            "qualification_id": "c" * 64,
            "aa0_harness_id": "d" * 64,
            "prewarm_run_id": "33129042894",
            "prewarm_completed_at_utc": "2026-08-28T08:00:00+00:00",
            "pr_assurance_run_id": "33129099999",
            "prospective_tree_sha": "e" * 40,
            "physical_tree_sha": "e" * 40,
        }

    def test_historical_v1_is_unchanged_and_deterministic(self) -> None:
        schema = json.loads((ROOT / "schemas/development/development_latency_canonical_dsai3v_v1.schema.json").read_text())
        policy = json.loads((ROOT / "registries/development/skills/development_latency_completion_receipt_v0_1.json").read_text())
        self.assertEqual(schema["$id"], "ovc-development-latency-canonical-dsai3v/v1")
        self.assertEqual(policy["canonical_receipt_schema"], "ovc-development-latency-canonical-dsai3v/v1")
        self.assertEqual(self.v1()["record_id"], FROZEN_V1_ID)
        self.assertEqual(self.v1(), self.v1())

    def test_v2_and_attachment_schemas_are_present(self) -> None:
        v2 = json.loads((ROOT / "schemas/development/development_latency_canonical_dsai3v_v2.schema.json").read_text())
        attachment = json.loads((ROOT / "schemas/development/dsai3v_completion_observability_attachment_v2.schema.json").read_text())
        self.assertEqual(v2["$id"], CANONICAL_COMPLETION_SCHEMA_V2)
        self.assertEqual(attachment["$id"], ATTACHMENT_SCHEMA_V2)
        self.assertTrue(set(TIMING_FIELDS).issubset(v2["properties"]["timing"]["properties"]))

    def test_v2_identity_is_deterministic_and_source_changes_are_identity_bearing(self) -> None:
        first = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(), timing_sources=self.sources(), aa0_observability=self.aa0()
        )
        second = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(), timing_sources=list(reversed(self.sources())), aa0_observability=self.aa0()
        )
        self.assertEqual(first, second)
        changed = self.sources()
        changed[0]["observed_at_utc"] = "2026-08-28T08:00:01Z"
        third = build_canonical_completion_latency_receipt_v2(v1_receipt=self.v1(), timing_sources=changed)
        self.assertNotEqual(first["record_id"], third["record_id"])
        self.assertEqual(first["timing"]["sources"], second["timing"]["sources"])

    def test_utc_normalization_missingness_and_subseconds(self) -> None:
        self.assertEqual(normalize_canonical_utc("2026-08-28T09:00:00+01:00"), "2026-08-28T08:00:00Z")
        self.assertEqual(normalize_canonical_utc("2026-08-28T08:00:00.123400Z"), "2026-08-28T08:00:00.123400Z")
        with self.assertRaises(ValueError):
            normalize_canonical_utc("2026-08-28T08:00:00")
        with self.assertRaises(ValueError):
            normalize_canonical_utc("not-a-time")
        unavailable = build_canonical_completion_latency_receipt_v2(v1_receipt=self.v1())
        self.assertEqual(unavailable["timing"]["status"], "UNAVAILABLE")
        self.assertTrue(all(unavailable["timing"][field] is None for field in TIMING_FIELDS))
        with self.assertRaises(ValueError):
            build_canonical_completion_latency_receipt_v2(
                v1_receipt=self.v1(),
                timing_sources=[source("pr_opened_at_utc", "GITHUB_PR", "pr", "")],
            )

    def test_partial_complete_ordering_warning_and_no_negative_latency(self) -> None:
        partial = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(), timing_sources=self.sources()[:1]
        )
        complete = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(), timing_sources=self.sources()
        )
        self.assertEqual(partial["timing"]["status"], "OBSERVED_PARTIAL")
        self.assertEqual(complete["timing"]["status"], "OBSERVED_COMPLETE")
        self.assertEqual(complete["timing"]["derived_latency_ms"]["pr_open_to_materialised_ms"], 50000)
        invalid = self.sources()
        invalid[-2]["observed_at_utc"] = "2026-08-28T07:59:00Z"
        receipt = build_canonical_completion_latency_receipt_v2(v1_receipt=self.v1(), timing_sources=invalid)
        self.assertTrue(any(row["code"] == "SOURCE_TIMESTAMP_ORDER_INVALID" for row in receipt["timing"]["warnings"]))
        self.assertIsNone(receipt["timing"]["derived_latency_ms"]["materialised_to_packet_completion_ms"])
        self.assertTrue(all(value is None or value >= 0 for value in receipt["timing"]["derived_latency_ms"].values()))

    def test_source_precedence_prefers_owner_receipt(self) -> None:
        receipt = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(),
            timing_sources=[
                source("physical_materialised_at_utc", "DEVOBS_RECEIPT", "devobs", "2026-08-28T08:00:51Z"),
                source("physical_materialised_at_utc", "PHYSICAL_MATERIALISATION_RECEIPT", "pmr", "2026-08-28T08:00:50Z"),
            ],
        )
        self.assertEqual(receipt["timing"]["physical_materialised_at_utc"], "2026-08-28T08:00:50Z")

    def test_identity_bearing_mismatches_fail_closed(self) -> None:
        receipt = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(), timing_sources=self.sources(), aa0_observability=self.aa0()
        )
        expectations = {
            "candidate_head_sha": "f" * 40,
            "pr_head_sha": "f" * 40,
            "pip_id": "f" * 64,
            "qualification_id": "f" * 64,
            "aa0_harness_id": "f" * 64,
            "prospective_tree_sha": "f" * 40,
            "physical_tree_sha": "f" * 40,
            "completion_receipt_id": "wrong",
        }
        for key, value in expectations.items():
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    validate_canonical_completion_latency_receipt_v2(receipt, expected={key: value})
        bad_head = self.aa0(); bad_head["pr_head_sha"] = "f" * 40
        with self.assertRaises(ValueError):
            build_canonical_completion_latency_receipt_v2(v1_receipt=self.v1(), aa0_observability=bad_head)
        bad_tree = self.aa0(); bad_tree["physical_tree_sha"] = "f" * 40
        with self.assertRaises(ValueError):
            build_canonical_completion_latency_receipt_v2(v1_receipt=self.v1(), aa0_observability=bad_tree)

    def test_v1_v2_reader_and_attachment_are_version_explicit(self) -> None:
        v1 = self.v1()
        v2 = build_canonical_completion_latency_receipt_v2(v1_receipt=v1)
        self.assertEqual(validate_compatible_canonical_completion_receipt(v1), CANONICAL_COMPLETION_SCHEMA)
        self.assertEqual(validate_compatible_canonical_completion_receipt(v2), CANONICAL_COMPLETION_SCHEMA_V2)
        attachment = build_completion_attachment_v2(
            programme_id=v1["programme_id"],
            packet_id=v1["packet_id"],
            completion_receipt_id=v1["completion_receipt_id"],
            development_latency_receipt=v2,
        )
        self.assertEqual(attachment.to_record()["schema"], ATTACHMENT_SCHEMA_V2)
        self.assertEqual(attachment.authority_effect, "NONE")

    def test_receipt_store_is_append_only_and_v1_cannot_be_overwritten(self) -> None:
        v1 = self.v1()
        v2 = build_canonical_completion_latency_receipt_v2(v1_receipt=v1)
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            store.put_record(v1, v1["record_id"])
            store.put_record(v2, v2["record_id"])
            self.assertTrue((Path(tmp) / f"{v1['record_id']}.json").is_file())
            self.assertTrue((Path(tmp) / f"{v2['record_id']}.json").is_file())
            changed = dict(v1); changed["packet_id"] = "rewritten"
            with self.assertRaises(Exception):
                store.put_record(changed, v1["record_id"])

    def test_no_new_storage_or_write_authority(self) -> None:
        binding = json.loads((ROOT / "registries/development/skills/VIT_COMPLETION_RECEIPTSTORE_BINDING_v0_1.json").read_text())
        receipt_store = binding["receipt_store"]
        self.assertEqual(receipt_store["implementation"], "ovc.development.skills.vit_materialisation.ReceiptStore")
        self.assertFalse(receipt_store["repository_fallback"])
        self.assertFalse(receipt_store["ephemeral_fallback"])
        self.assertEqual(binding["controller"], "DSAI_VIT_PHYSICAL_CONTROLLER")
        self.assertEqual(binding["physical_gateway"], "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY")
        self.assertEqual(build_canonical_completion_latency_receipt_v2(v1_receipt=self.v1())["authority_effect"], "NONE")

    def test_post_merge_runtime_emits_v1_and_v2_without_changing_v1_index(self) -> None:
        transaction = PhysicalMaterialisationTransaction(
            vit_generation_id="g",
            ticket_id="ticket",
            train_generation_id="train",
            expected_predecessor_commit="1" * 40,
            expected_predecessor_tree="2" * 40,
            expected_result_tree="3" * 40,
            authority_frontier_id="4" * 64,
            assurance_frontier_id="5" * 64,
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )
        trace = {
            "schema": "ovc-development-observability-trace-summary/v1",
            "record_id": "9" * 64,
            "completed_at_utc": "2026-08-28T08:00:50Z",
            "total_wall_ms": 10,
            "throughput": {},
            "latency_decomposition": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            result = persist_physical_completion(
                transaction=transaction,
                observed_commit="a" * 40,
                observed_tree="3" * 40,
                programme_id="OVC-DSAI-VIT-v0.3",
                packet_id="P",
                implementation_ref="github:pr:1:head:" + "6" * 40,
                qa_ref="q",
                gate_decision_ref="d",
                payload_id="7" * 64,
                next_packet=None,
                receipt_store=store,
                trace_summary=trace,
            )
            self.assertTrue((Path(tmp) / f"{result['v2_development_latency_receipt_id']}.json").is_file())
            self.assertTrue((Path(tmp) / f"{result['v2_attachment_id']}.json").is_file())
            self.assertIn(f"completion_receipt_id:{result['completion_receipt_id']}", store.rebuild_index())

    def test_canonical_identity_rejects_tamper(self) -> None:
        receipt = build_canonical_completion_latency_receipt_v2(
            v1_receipt=self.v1(), timing_sources=self.sources(), aa0_observability=self.aa0()
        )
        receipt["timing"]["status"] = "UNAVAILABLE"
        with self.assertRaises(ValueError):
            validate_canonical_completion_latency_receipt_v2(receipt)


if __name__ == "__main__":
    unittest.main()
