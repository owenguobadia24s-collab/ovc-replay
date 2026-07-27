from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = ROOT / "docs/releases/prospective-source-v0-1/rps-wp3/RPS_WP3_COMPACT_COMPUTE_EVIDENCE_INDEX.json"
STATE_PATH = ROOT / "registries/research_operations/prospective_source/RPS_G3_ACCEPTANCE_STATE_v0_1.json"


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class RpsWp3CompactComputeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def test_exact_compute_and_binding_identities_reproduce(self) -> None:
        run_identity = {
            "slice_id": self.index["slice_id"],
            "source_manifest_sha256": self.index["source_manifest_sha256"],
            "code_commit": self.index["code_commit"],
            "operation_mode": self.index["operation_mode"],
            "admissible_cutoff_utc": self.index["admissible_cutoff_utc"],
            "output_manifest_sha256": self.index["output_manifest_sha256"],
        }
        self.assertEqual(
            self.index["run_id"],
            f"RPS.RUN.{canonical_hash(run_identity)[:24]}",
        )
        binding = self.index["binding"]
        binding_identity = {
            "research_line_id": binding["research_line_id"],
            "active_c2_model_release_id": binding["active_c2_model_release_id"],
            "source_slice_id": self.index["slice_id"],
            "source_manifest_sha256": self.index["source_manifest_sha256"],
            "compute_run_id": self.index["run_id"],
            "eligible_data_through_utc": binding["eligible_data_through_utc"],
        }
        self.assertEqual(
            self.index["binding_id"],
            f"RPS.BINDING.{canonical_hash(binding_identity)[:24]}",
        )

    def test_compact_byte_inventory_is_exact(self) -> None:
        compact = {item["name"]: item for item in self.index["compact_files"]}
        self.assertEqual(
            compact,
            {
                "coverage.json": {
                    "name": "coverage.json",
                    "sha256": "e3cbbe8676ce0058be8385affdd51f74fd0816a59c5eecdb121500705da928b5",
                    "size_bytes": 806,
                },
                "compute-receipt.json": {
                    "name": "compute-receipt.json",
                    "sha256": "bbd36c055fe23e32daadd646323d04b4ee125c224c98540915e8c1bb4a6aa2df",
                    "size_bytes": 1345,
                },
                "output-manifest.json": {
                    "name": "output-manifest.json",
                    "sha256": "af0410d58f8b6522129a0162f9741c6b7bc5485526848d64199cdbc60256f7be",
                    "size_bytes": 4632,
                },
                "prospective-compute-run.json": {
                    "name": "prospective-compute-run.json",
                    "sha256": "c25632febb84a8d3604390988a042fa8b30e1484381a17d4201ab58388e78e41",
                    "size_bytes": 496,
                },
                "prospective-source-binding.json": {
                    "name": "prospective-source-binding.json",
                    "sha256": "d4cf2c272b4b7125a89cbf95b3b8943a2e68e8b2027608eafda058d6159ac576",
                    "size_bytes": 1069,
                },
            },
        )
        self.assertEqual(
            self.index["output_manifest_file_sha256"],
            compact["output-manifest.json"]["sha256"],
        )
        self.assertEqual(
            self.index["compute_run_file_sha256"],
            compact["prospective-compute-run.json"]["sha256"],
        )
        self.assertEqual(
            self.index["binding_file_sha256"],
            compact["prospective-source-binding.json"]["sha256"],
        )

    def test_coverage_closes_without_incomplete_parent_consumption(self) -> None:
        coverage = self.index["coverage"]
        self.assertEqual(coverage["15M"], {
            "clock": "15M", "total": 288, "complete": 271,
            "unavailable": 17, "incomplete_parent_policy": "EXCLUDE_NO_SYNTHESIS",
        })
        self.assertEqual(coverage["2H_A_L"], {
            "clock": "2H_A_L", "total": 36, "complete": 30,
            "unavailable": 6, "incomplete_parent_policy": "EXCLUDE_NO_SYNTHESIS",
        })
        self.assertEqual(coverage["c1_record_count"], 2 * (271 + 30))
        self.assertEqual(coverage["c2_state_count"], 2 * (30 + 271 + 271))
        self.assertEqual(coverage["c2_transition_count"], 954)
        self.assertEqual(coverage["qa_state"], "PASS_GAPPED_EXCLUSION")
        self.assertEqual(coverage["incomplete_parent_consumption"], "DENIED")
        for field in (
            "repair_performed", "forward_fill_performed",
            "interpolation_performed", "synthesis_performed",
        ):
            self.assertFalse(coverage[field])

    def test_payload_and_authority_remain_bounded(self) -> None:
        payload = self.index["payload_inventory"]
        self.assertEqual(payload["file_count"], 21)
        self.assertEqual(payload["payload_bytes"], 5_557_327)
        self.assertEqual(sum(payload["scope_inventory"].values()), 21)
        self.assertEqual(
            payload["coverage_file"]["sha256"],
            next(item["sha256"] for item in self.index["compact_files"] if item["name"] == "coverage.json"),
        )
        authority = self.index["authority"]
        self.assertEqual(authority["release_status"], "NOT_A_RELEASE")
        self.assertEqual(authority["selector_eligibility"], "NONE")
        self.assertEqual(authority["r2_publication"], "DENIED")
        self.assertEqual(authority["validation_consumption"], "DENIED")
        self.assertEqual(authority["live_prospective_append"], "DENIED")
        self.assertFalse(authority["active_research_triage"])
        self.assertFalse(authority["write_authority"])
        self.assertFalse(authority["provider_network_access_performed"])
        self.assertTrue(authority["deterministic_replay"])
        self.assertTrue(authority["lineage_complete"])

    def test_machine_state_names_next_packet_without_activation(self) -> None:
        self.assertEqual(self.state["packet_id"], "RPS-WP3")
        self.assertEqual(self.state["gate_id"], "RPS-G3")
        self.assertEqual(self.state["next_packet"], "RPS-WP4")
        self.assertEqual(self.state["run_id"], self.index["run_id"])
        self.assertEqual(self.state["binding_id"], self.index["binding_id"])
        self.assertIsNone(self.state["active_binding_id"])
        self.assertFalse(self.state["active_research_triage"])
        self.assertFalse(self.state["write_authority"])
        self.assertEqual(self.state["live_prospective_append"], "DENIED")


if __name__ == "__main__":
    unittest.main()
