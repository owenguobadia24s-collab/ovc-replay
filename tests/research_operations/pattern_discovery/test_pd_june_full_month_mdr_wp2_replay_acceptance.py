from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr" / "wp2-replay"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_PROGRAMME_STATE_v0_1.json"


def load(name: str) -> dict:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def logical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


class PDJuneFullMonthMDRWP2ReplayAcceptanceTests(unittest.TestCase):
    def test_six_compact_files_and_manifest_bindings_remain_exact(self) -> None:
        index = load("PD_JUNE_FULL_MONTH_MDR_WP2_REPLAY_ACCEPTANCE_INDEX.json")
        self.assertEqual(index["acceptance_status"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertEqual(index["merge_commit"], "fedc20ab92f0465e5c84d7626f859866c9ad1f00")
        self.assertEqual(len(index["compact_files"]), 6)
        for item in index["compact_files"]:
            path = BASE / item["name"]
            self.assertEqual(path.stat().st_size, item["size_bytes"])
            self.assertEqual(sha(path), item["sha256"])
        manifest = load("output-manifest.json")
        body = dict(manifest)
        claimed = body.pop("output_manifest_sha256")
        self.assertEqual(logical_sha(body), claimed)
        run = load("replay-run.json")
        receipt = load("replay-receipt.json")
        binding = load("prospective-source-binding.json")
        self.assertEqual(run["run_id"], receipt["run_id"])
        self.assertEqual(run["run_id"], binding["compute_run_id"])
        self.assertEqual(run["output_manifest_sha256"], claimed)
        self.assertEqual(receipt["output_manifest_sha256"], claimed)
        self.assertEqual(receipt["output_manifest_file_sha256"], sha(BASE / "output-manifest.json"))
        self.assertEqual(receipt["replay_run_file_sha256"], sha(BASE / "replay-run.json"))
        self.assertEqual(receipt["binding_file_sha256"], sha(BASE / "prospective-source-binding.json"))
        self.assertEqual(run["deterministic_independent_rerun"], "PASS_BYTE_IDENTICAL")

    def test_population_boundary_and_no_repair_acceptance_remain_exact(self) -> None:
        receipt = load("replay-receipt.json")
        coverage = load("coverage.json")
        target = load("target-eligibility.json")
        self.assertEqual((receipt["c1_record_count"], receipt["target_c1_record_count"]), (4958, 4526))
        self.assertEqual((receipt["c2_state_count"], receipt["target_c2_state_count"]), (9420, 8598))
        self.assertEqual((receipt["c2_transition_count"], receipt["target_c2_transition_count"]), (7345, 6783))
        self.assertEqual(coverage["source_boundary_insufficiency"], 0)
        self.assertEqual(target["window_not_complete_due_solely_to_june_calendar_boundary"], 0)
        self.assertEqual(coverage["qa_state"], "PASS_EXPLICIT_PAIRED_SPARSE_CENSORING")
        for field in ("repair_performed", "interpolation_performed", "forward_fill_performed", "synthesis_performed"):
            self.assertFalse(coverage[field])

    def test_merge_receipt_and_authority_survive_wp3_progression(self) -> None:
        receipt = load("replay-receipt.json")
        binding = load("prospective-source-binding.json")
        decision = load("PD_JUNE_FULL_MONTH_MDR_WP2_REPLAY_DELEGATED_DECISION.json")
        merge_receipt = load("PD_JUNE_FULL_MONTH_MDR_WP2_REPLAY_MERGE_RECEIPT.json")
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(receipt["release_status"], "NOT_A_RELEASE")
        self.assertEqual(receipt["selector_eligibility"], "NONE")
        self.assertEqual(receipt["r2_publication"], "DENIED")
        self.assertEqual(receipt["validation_consumption"], "DENIED")
        self.assertFalse(receipt["write_authority"])
        self.assertFalse(binding["active_research_triage"])
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["status"], "COMPLETED_SQUASH_MERGED_WP3_READY")
        self.assertEqual(merge_receipt["pull_request"], 200)
        self.assertEqual(merge_receipt["final_head"], "89d06f5e4578c3e945c7b7dd443ef573ae743f85")
        self.assertEqual(merge_receipt["merge_commit"], "fedc20ab92f0465e5c84d7626f859866c9ad1f00")
        self.assertEqual(merge_receipt["merge_result"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertEqual(state["acceptance_merge_commit"], merge_receipt["merge_commit"])
        self.assertEqual(state["replay_status"], "PASS_ACCEPTED_FOR_WP3")
        self.assertEqual(state["packet_id"], "PD-JUNE-FM-WP3")
        self.assertEqual(state["next_packet"], "PD-JUNE-FM-G2")
        self.assertEqual(state["next_packet_authority"], "OPERATOR_REQUIRED_BLINDED_REVIEW")
        self.assertEqual(state["release_status"], "NOT_A_RELEASE")
        self.assertEqual(state["selector_eligibility"], "NONE")
        self.assertEqual(state["r2_publication"], "DENIED")
        self.assertEqual(state["validation_consumption"], "DENIED")
        self.assertFalse(state["write_authority"])


if __name__ == "__main__":
    unittest.main()
