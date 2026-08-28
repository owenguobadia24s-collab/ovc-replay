from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ovc.development.dsai3v_completion_observability import (
    build_canonical_completion_latency_receipt,
)
from ovc.development.dsai3v_completion_observability_v2 import (
    build_canonical_completion_latency_receipt_v2,
)
from ovc.development.dsai3v_completion_source_binding import (
    build_github_completion_source_binding,
    has_source_bound_pr_to_materialised,
)
from ovc.development.skills.vit_local_completion_executor import (
    FREEZE_SCHEMA,
    complete_frozen_transaction,
)
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    ReceiptStore,
)
from ovc.development.skills.vit_routing import SIQ_GATEWAY, VIT_CONTROLLER
from tools.ci.vit_post_merge_completion_late_binding import _already_completed


class Dsai3vCompletionSourceBindingTests(unittest.TestCase):
    def observations(self):
        pr = {
            "number": 1393,
            "created_at": "2026-08-28T10:56:59Z",
            "merged_at": "2026-08-28T10:59:59Z",
        }
        runs = (
            {"id": 100, "name": "tests"},
            {"id": 200, "name": "OVC tiered test selection shadow"},
        )
        jobs = {
            100: (
                {
                    "id": 101,
                    "name": "canonical pytest shard assurance plan",
                    "status": "completed",
                    "conclusion": "success",
                    "completed_at": "2026-08-28T10:57:22Z",
                },
                {
                    "id": 102,
                    "name": "canonical pytest shard ${{ matrix.shard }}",
                    "status": "completed",
                    "conclusion": "skipped",
                    "completed_at": "2026-08-28T10:57:23Z",
                },
            ),
            200: (
                {
                    "id": 201,
                    "name": "OVC profile assurance",
                    "status": "completed",
                    "conclusion": "success",
                    "completed_at": "2026-08-28T10:57:30Z",
                },
                {
                    "id": 202,
                    "name": "SIQ READY admission",
                    "status": "completed",
                    "conclusion": "success",
                    "completed_at": "2026-08-28T10:57:39Z",
                },
                {
                    "id": 203,
                    "name": "OVC merge readiness",
                    "status": "completed",
                    "conclusion": "success",
                    "completed_at": "2026-08-28T10:57:53Z",
                },
            ),
        }
        return pr, runs, jobs

    def test_github_binding_uses_direct_sources_and_measures_180_seconds(self) -> None:
        pr, runs, jobs = self.observations()
        binding = build_github_completion_source_binding(
            pr=pr,
            workflow_runs=runs,
            jobs_by_run=jobs,
        )
        v1 = build_canonical_completion_latency_receipt(
            programme_id="OVC-DSAI-VIT-v0.3",
            packet_id="packet",
            completion_receipt_id="completion",
        )
        v2 = build_canonical_completion_latency_receipt_v2(
            v1_receipt=v1,
            timing_sources=binding["timing_sources"],
            aa0_observability=binding["aa0_observability"],
        )
        self.assertEqual(v2["timing"]["status"], "OBSERVED_PARTIAL")
        self.assertEqual(
            v2["timing"]["derived_latency_ms"]["pr_open_to_materialised_ms"],
            180000.0,
        )
        self.assertEqual(v2["timing"]["warnings"], [])
        self.assertEqual(binding["aa0_observability"]["pr_assurance_run_id"], "100")
        self.assertFalse(binding["aa0_observability"]["canonical_shards_executed"])
        self.assertTrue(has_source_bound_pr_to_materialised(v2))

    def test_complete_frozen_transaction_persists_source_bound_v2_ids(self) -> None:
        pr, runs, jobs = self.observations()
        binding = build_github_completion_source_binding(
            pr=pr,
            workflow_runs=runs,
            jobs_by_run=jobs,
        )
        transaction = PhysicalMaterialisationTransaction(
            vit_generation_id="placement",
            ticket_id="ticket",
            train_generation_id="train",
            expected_predecessor_commit="a" * 40,
            expected_predecessor_tree="b" * 40,
            expected_result_tree="c" * 40,
            authority_frontier_id="authority",
            assurance_frontier_id="assurance",
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )
        freeze = {
            "schema": FREEZE_SCHEMA,
            "controller": VIT_CONTROLLER,
            "physical_gateway": SIQ_GATEWAY,
            "pr_number": 1393,
            "head_sha": "d" * 40,
            "pip_id": "f" * 64,
            "generation_id": transaction.vit_generation_id,
            "placement_id": transaction.vit_generation_id,
            "transaction": transaction.__dict__,
            "transaction_id": transaction.transaction_id,
            "completion_context": {
                "programme_id": "OVC-DSAI-VIT-v0.3",
                "packet_id": "packet",
                "implementation_ref": f"github:pr:1393:head:{'d' * 40}",
                "qa_ref": "qa",
                "gate_decision_ref": "gate",
                "payload_id": "f" * 64,
                "next_packet": None,
            },
            "authority_effect": "NONE",
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp))
            proof = complete_frozen_transaction(
                freeze=freeze,
                observed_commit="e" * 40,
                observed_tree="c" * 40,
                receipt_store=store,
                completion_timing_sources=binding["timing_sources"],
                completion_aa0_observability=binding["aa0_observability"],
            )
            ids = proof["v2_receipt_ids"]
            v2 = json.loads(
                (store.root / f"{ids['v2_development_latency_receipt_id']}.json").read_text()
            )
            self.assertEqual(
                v2["timing"]["derived_latency_ms"]["pr_open_to_materialised_ms"],
                180000.0,
            )
            self.assertEqual(v2["aa0"]["candidate_head_sha"], "d" * 40)
            self.assertEqual(v2["aa0"]["pr_head_sha"], "d" * 40)
            self.assertEqual(v2["aa0"]["pip_id"], "f" * 64)
            self.assertEqual(v2["aa0"]["prospective_tree_sha"], "c" * 40)
            self.assertEqual(v2["aa0"]["physical_tree_sha"], "c" * 40)
            self.assertTrue(
                (store.root / f"{ids['v2_attachment_id']}.json").is_file()
            )

    def test_existing_blank_v2_replays_but_historical_v1_only_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp))
            proof_root = store.root / "proofs"
            proof_root.mkdir()
            completion_id = "completion-current"
            proof = {
                "observed_commit": "1" * 40,
                "exact_tree_equal": True,
                "four_content_addressed_receipts_present": True,
                "receipt_ids": {"completion_receipt_id": completion_id},
                "proof_id": "proof-current",
            }
            (proof_root / "proof-current.json").write_text(json.dumps(proof))
            v1 = build_canonical_completion_latency_receipt(
                programme_id="OVC-DSAI-VIT-v0.3",
                packet_id="current",
                completion_receipt_id=completion_id,
            )
            blank_v2 = build_canonical_completion_latency_receipt_v2(v1_receipt=v1)
            store.put_record(blank_v2, blank_v2["record_id"])
            self.assertFalse(_already_completed(store, "1" * 40))

        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp))
            proof_root = store.root / "proofs"
            proof_root.mkdir()
            historical = {
                "observed_commit": "2" * 40,
                "exact_tree_equal": True,
                "four_content_addressed_receipts_present": True,
                "receipt_ids": {"completion_receipt_id": "historical"},
                "proof_id": "proof-historical",
            }
            (proof_root / "proof-historical.json").write_text(json.dumps(historical))
            self.assertTrue(_already_completed(store, "2" * 40))


if __name__ == "__main__":
    unittest.main()
