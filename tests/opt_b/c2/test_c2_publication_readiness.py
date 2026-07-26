from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "opt_b" / "review_c2_publication_readiness.py"
spec = importlib.util.spec_from_file_location("review_c2_publication_readiness", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class C2PublicationReadinessTests(unittest.TestCase):
    def test_exact_final_candidate_artifacts_are_pinned(self) -> None:
        self.assertEqual(module.SOURCE_RUN_ID, 30212281089)
        self.assertEqual(module.SOURCE_COMMIT, "1d72d2332e71639e7eee42bef96357e4640d4fb8")
        self.assertEqual(module.ARTIFACTS["DISCOVERY"]["id"], 8634803012)
        self.assertEqual(module.ARTIFACTS["DEVELOPMENT"]["id"], 8634803579)
        self.assertEqual(module.ARTIFACTS["GATE_PACKET"]["id"], 8634803684)

    def test_candidate_tree_and_release_manifests_are_pinned(self) -> None:
        self.assertEqual(module.CANDIDATE_TREE_SHA256, "f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd")
        self.assertEqual(module.EXPECTED["DISCOVERY"]["manifest_sha256"], "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33")
        self.assertEqual(module.EXPECTED["DEVELOPMENT"]["manifest_sha256"], "8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e")

    def test_exact_parent_manifests_are_pinned(self) -> None:
        discovery = module.EXPECTED["DISCOVERY"]
        development = module.EXPECTED["DEVELOPMENT"]
        self.assertEqual(discovery["parent_opt_a_manifest_sha256"], "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c")
        self.assertEqual(development["parent_opt_a_manifest_sha256"], "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc")
        self.assertEqual(discovery["parent_c1_manifest_sha256"], "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2")
        self.assertEqual(development["parent_c1_manifest_sha256"], "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017")

    def test_expected_totals_match_frozen_gate(self) -> None:
        releases = module.EXPECTED.values()
        self.assertEqual(sum(item["state_record_count"] for item in releases), 404_434)
        self.assertEqual(sum(item["transition_record_count"] for item in releases), 323_910)
        self.assertEqual(sum(item["manifest_bound_bytes"] for item in releases), 872_867_602)
        self.assertEqual(sum(item["manifest_bound_file_count"] for item in releases), 36)

    def test_gate_packet_requires_no_publication_or_activation_at_freeze(self) -> None:
        packet = {
            "decision": "PASS_LOCAL_CANDIDATE_RELEASE_FROZEN",
            "verification": {
                "candidate_tree_sha256": module.CANDIDATE_TREE_SHA256,
                "full_byte_local_verification": "PASS",
                "blocking_qa_issues": 0,
                "unresolved_qa_issues": 0,
            },
            "authority_delta": {
                "publication": "NONE",
                "selector": "NONE",
                "activation": "NONE",
                "validation_consumption": "LOCKED_UNCONSUMED",
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")
            module.verify_gate_packet(path)

    def test_canonical_serialization_is_stable(self) -> None:
        self.assertEqual(module.canonical_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}\n')


if __name__ == "__main__":
    unittest.main()
