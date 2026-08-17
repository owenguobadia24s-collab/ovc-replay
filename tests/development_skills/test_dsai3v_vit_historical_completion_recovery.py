from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_historical_completion_recovery import (
    AUTHORIZED_HEAD,
    AUTHORIZED_MERGE,
    AUTHORIZED_PIP,
    AUTHORIZED_GENERATION,
    AUTHORIZED_PREDECESSOR_TREE,
    AUTHORIZED_RESULT_TREE,
    COMPLETION_SCHEMA,
    DECISION_SCHEMA,
    recover_historical_effective_write_completion,
    reconstruct_historical_completion,
)
from ovc.development.skills.vit_local_completion_executor import decode_freeze_marker
from ovc.development.skills.vit_materialisation import ReceiptStore


ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = ROOT / "docs/programmes/system-atlas-v0-1/wp10/ATLAS_WP10_HISTORICAL_COMPLETION_RECOVERY_DECISION.json"
SOURCE_CENSUS_PATH = ROOT / "docs/programmes/system-atlas-v0-1/wp10/ATLAS_WP10_HISTORICAL_COMPLETION_RECOVERY_SOURCE_CENSUS.json"


class HistoricalCompletionRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

    def _recover(self, store: ReceiptStore):
        return recover_historical_effective_write_completion(
            decision=self.decision,
            receipt_store=store,
            current_main_before="a" * 40,
            current_main_after="a" * 40,
            implementation_ref=f"github:pr:1047:head:{AUTHORIZED_HEAD}",
            qa_ref=f"github:pr:1047:head:{AUTHORIZED_HEAD}:required-assurance",
            gate_decision_ref="atlas:ATLAS-G10:PASS_DELEGATED_AUTO_RATIFICATION",
            next_packet="ATLAS-G-OBSERVABILITY-ACTIVATE",
            siq_receipts=({"schema": "siq/v1", "record_id": "siq-ready", "status": "SIQ_READY"},),
        )

    def test_decision_schema_and_identity_are_exact(self) -> None:
        logical = {key: value for key, value in self.decision.items() if key != "recovery_decision_id"}
        self.assertEqual(
            self.decision["recovery_decision_id"],
            canonical_sha256(logical, role="DSAI3V_HISTORICAL_COMPLETION_RECOVERY_DECISION"),
        )
        self.assertEqual(self.decision["authority_effect"], "NONE")
        self.assertEqual(self.decision["precedent_effect"], "NONE_SINGLE_USE")
        self.assertEqual(
            self.decision["normal_prospective_requirement"],
            "PMT_AND_PREWRITE_FREEZE_REQUIRED_UNCHANGED",
        )

    def test_absent_freeze_source_census_is_content_addressed(self) -> None:
        census = json.loads(SOURCE_CENSUS_PATH.read_text(encoding="utf-8"))
        logical = {key: value for key, value in census.items() if key != "census_id"}
        self.assertEqual(
            census["census_id"],
            canonical_sha256(logical, role="DSAI3V_HISTORICAL_COMPLETION_RECOVERY_SOURCE_CENSUS"),
        )
        self.assertEqual(census["prewrite_freeze_status"], "ABSENT_NOT_EMITTED")
        self.assertEqual(census["sources"]["successful_vit_routing_preflight"]["freeze_marker_count"], 0)
        self.assertEqual(census["sources"]["actions_artifacts"]["artifact_count"], 0)

    def test_subject_is_single_use_and_exact(self) -> None:
        self.assertEqual(self.decision["schema"], DECISION_SCHEMA)
        self.assertEqual(self.decision["pr_number"], 1047)
        self.assertEqual(self.decision["physical_merge_sha"], AUTHORIZED_MERGE)
        self.assertEqual(self.decision["pip_id"], AUTHORIZED_PIP)
        self.assertEqual(self.decision["vit_generation_id"], AUTHORIZED_GENERATION)
        self.assertEqual(self.decision["predecessor_tree"], AUTHORIZED_PREDECESSOR_TREE)
        self.assertEqual(self.decision["observed_physical_tree"], AUTHORIZED_RESULT_TREE)

    def test_recovery_is_idempotent_and_has_exactly_one_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            first = self._recover(store)
            inventory = sorted(path.relative_to(tmp).as_posix() for path in Path(tmp).rglob("*.json"))
            second = self._recover(store)
            self.assertEqual(first, second)
            self.assertEqual(inventory, sorted(path.relative_to(tmp).as_posix() for path in Path(tmp).rglob("*.json")))
            completions = []
            for path in Path(tmp).glob("*.json"):
                value = json.loads(path.read_text(encoding="utf-8"))
                if value.get("schema") == COMPLETION_SCHEMA:
                    completions.append(value)
            self.assertEqual(len(completions), 1)
            self.assertNotEqual(first.recovery_attempt_id, first.recovery_decision_id)

    def test_reconstruction_and_unavailable_devobs_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            bundle = self._recover(store)
            rebuilt = reconstruct_historical_completion(receipt_store=store, decision=self.decision)
            self.assertEqual(rebuilt["completion_receipt_id"], bundle.completion_receipt_id)
            devobs = json.loads((Path(tmp) / f"{bundle.development_latency_receipt_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(devobs["latency"]["status"], "UNAVAILABLE")
            self.assertEqual(devobs["async_assurance"]["status"], "UNAVAILABLE")

    def test_no_recovery_record_implies_an_original_pmt(self) -> None:
        forbidden = {"transaction_id", "materialisation_transaction_id", "ticket_id", "assurance_frontier_id"}
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(tmp)
            self._recover(store)
            for path in Path(tmp).rglob("*.json"):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(forbidden.isdisjoint(value.keys()), path.name)

    def test_recovery_fails_if_main_moves_and_prospective_freeze_stays_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(VitContractError, "HISTORICAL_RECOVERY_MAIN_REF_CHANGED"):
                recover_historical_effective_write_completion(
                    decision=self.decision,
                    receipt_store=ReceiptStore(tmp),
                    current_main_before="a" * 40,
                    current_main_after="b" * 40,
                    implementation_ref="impl",
                    qa_ref="qa",
                    gate_decision_ref="gate",
                    next_packet=None,
                    siq_receipts=(),
                )
        with self.assertRaisesRegex(VitContractError, "VIT_LIVE_TRANSACTION_FREEZE_NOT_UNIQUE"):
            decode_freeze_marker("no pre-write freeze marker")


if __name__ == "__main__":
    unittest.main()
